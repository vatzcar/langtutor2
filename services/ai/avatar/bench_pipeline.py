"""bench_pipeline.py — end-to-end MuseTalk render-time benchmark.

Run INSIDE the avatar container (or any env where MuseTalkWorker can load):

    python /app/src/bench_pipeline.py \
        --audio /tmp/sample.wav \
        --source /tmp/persona.mp4 \
        --runs 5 \
        --batch-size 8

The script creates its OWN MuseTalkWorker (independent of the FastAPI
process), so you can pass -e MUSETALK_USE_NVENC=1 to docker exec and the
bench will pick it up via os.environ.

Output: per-run wall times, average/median/min/max, real-time ratio, and
projected cost per minute of rendered avatar.
"""

from __future__ import annotations

import argparse
import os
import shutil
import statistics
import sys
import tempfile
import time
import wave
from pathlib import Path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _audio_duration_seconds(audio_path: Path) -> float:
    """Return duration of a WAV file in seconds using the stdlib wave module.

    Falls back to an ffprobe call for non-WAV formats.
    """
    suffix = audio_path.suffix.lower()
    if suffix == ".wav":
        try:
            with wave.open(str(audio_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames / rate
        except wave.Error:
            pass  # fall through to ffprobe

    # ffprobe fallback for MP3 / AAC / etc.
    import subprocess
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed on {audio_path}:\n{result.stderr}"
        )
    import json
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    return duration


def _build_worker() -> object:
    """Construct a MuseTalkWorker using env vars (same logic as app.py)."""
    repo_dir = Path(os.environ.get("MUSETALK_REPO_DIR", "/app/MuseTalk"))
    models_dir = Path(os.environ.get("MUSETALK_MODELS_DIR", "/app/MuseTalk/models"))
    version = os.environ.get("MUSETALK_VERSION", "v15")
    device = os.environ.get("MUSETALK_DEVICE", "cuda")
    use_fp16 = os.environ.get("MUSETALK_FP16", "1") not in {"0", "false", "False", ""}

    # MuseTalk resolves weight paths relative to its own repo dir.
    if repo_dir.is_dir():
        os.chdir(repo_dir)
        print(f"[bench] cwd → {repo_dir}", flush=True)

    # Import worker AFTER chdir so relative-path resolution matches app.py.
    from worker import MuseTalkWorker  # noqa: PLC0415

    if version == "v15":
        model_dir = models_dir / "musetalkV15"
        unet_path = model_dir / "unet.pth"
    else:
        model_dir = models_dir / "musetalk"
        unet_path = model_dir / "pytorch_model.bin"

    print(
        f"[bench] loading worker: version={version} device={device} fp16={use_fp16}",
        flush=True,
    )
    t0 = time.perf_counter()
    worker = MuseTalkWorker(
        unet_model_path=unet_path,
        unet_config=model_dir / "musetalk.json",
        whisper_dir=models_dir / "whisper",
        version=version,
        device=device,
        use_float16=use_fp16,
    )
    elapsed = time.perf_counter() - t0
    print(f"[bench] worker ready in {elapsed:.1f}s", flush=True)
    return worker


def _cost_per_minute(render_seconds: float, hourly_cost_usd: float) -> float:
    """Dollar cost to render one minute of avatar output.

    Formula:
        (render_time_s / 60) * (hourly_cost / 60)

    i.e. cost = fraction_of_GPU_hour_per_minute_of_avatar × hourly_rate.
    """
    return (render_seconds / 60.0) * (hourly_cost_usd / 60.0)


def _fmt_row(label: str, render_s: float, audio_s: float, cost: float) -> str:
    rt_ratio = render_s / audio_s if audio_s > 0 else float("inf")
    return (
        f"  {label:<28}  render={render_s:>7.2f}s  "
        f"RT-ratio={rt_ratio:>5.2f}x  cost/min=${cost:.5f}"
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark MuseTalk end-to-end render time.",
    )
    parser.add_argument("--audio", required=True, type=Path,
                        help="Path to the WAV audio file.")
    parser.add_argument("--source", required=True, type=Path,
                        help="Path to the source MP4 or image.")
    parser.add_argument("--runs", type=int, default=5,
                        help="Number of benchmark runs (default: 5).")
    parser.add_argument("--batch-size", type=int, default=8, dest="batch_size",
                        help="UNet batch size (default: 8; must match warmup).")
    parser.add_argument("--hourly-cost", type=float, default=0.40,
                        dest="hourly_cost",
                        help="GPU hourly cost in USD (default: 0.40 for RTX 4090 TensorDock).")
    args = parser.parse_args()

    audio_path: Path = args.audio.resolve()
    source_path: Path = args.source.resolve()

    if not audio_path.exists():
        sys.exit(f"[bench] ERROR: audio file not found: {audio_path}")
    if not source_path.exists():
        sys.exit(f"[bench] ERROR: source file not found: {source_path}")

    # Determine audio duration.
    try:
        audio_duration = _audio_duration_seconds(audio_path)
    except Exception as exc:
        sys.exit(f"[bench] ERROR: could not determine audio duration: {exc}")
    print(f"[bench] audio duration: {audio_duration:.2f}s", flush=True)

    nvenc_flag = os.environ.get("MUSETALK_USE_NVENC", "0") in {"1", "true", "True"}
    print(
        f"[bench] MUSETALK_USE_NVENC={'1 (GPU h264_nvenc)' if nvenc_flag else '0 (CPU libx264)'}",
        flush=True,
    )

    # Build the worker once.
    worker = _build_worker()

    run_times: list[float] = []

    for run_idx in range(1, args.runs + 1):
        workdir = Path(tempfile.mkdtemp(prefix=f"bench-run{run_idx}-"))
        try:
            print(f"\n[bench] --- run {run_idx}/{args.runs} ---", flush=True)
            t_start = time.perf_counter()
            worker.infer(
                audio_path=audio_path,
                source_path=source_path,
                output_dir=workdir,
                batch_size=args.batch_size,
            )
            elapsed = time.perf_counter() - t_start
            run_times.append(elapsed)
            cost = _cost_per_minute(elapsed, args.hourly_cost)
            rt_ratio = elapsed / audio_duration if audio_duration > 0 else float("inf")
            print(
                f"[bench] run {run_idx}: {elapsed:.2f}s  "
                f"RT-ratio={rt_ratio:.2f}x  cost/min=${cost:.5f}",
                flush=True,
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    if not run_times:
        sys.exit("[bench] ERROR: no runs completed.")

    # Summary.
    avg = statistics.mean(run_times)
    med = statistics.median(run_times)
    mn = min(run_times)
    mx = max(run_times)

    # Exclude run 1 from "steady-state" stats (torch.compile JIT / cache miss).
    if len(run_times) > 1:
        steady_avg = statistics.mean(run_times[1:])
        steady_med = statistics.median(run_times[1:])
    else:
        steady_avg = avg
        steady_med = med

    print("\n" + "=" * 72)
    print("BENCHMARK SUMMARY")
    print("=" * 72)
    print(f"  audio file  : {audio_path.name}")
    print(f"  source file : {source_path.name}")
    print(f"  audio dur   : {audio_duration:.2f}s")
    print(f"  runs        : {args.runs}")
    print(f"  batch_size  : {args.batch_size}")
    print(f"  hourly_cost : ${args.hourly_cost:.2f}")
    encode_mode = "h264_nvenc (GPU)" if nvenc_flag else "libx264 ultrafast (CPU)"
    print(f"  encode      : {encode_mode}")
    print()
    print("  Per-run wall times (s):")
    for i, t in enumerate(run_times, start=1):
        marker = "  *first run*" if i == 1 else ""
        print(f"    run {i:>2}: {t:>7.2f}s{marker}")
    print()
    print(f"  All-runs avg  : {avg:.2f}s  (incl. run 1)")
    print(f"  Steady-st avg : {steady_avg:.2f}s  (runs 2+)")
    print(f"  Median        : {med:.2f}s")
    print(f"  Min           : {mn:.2f}s")
    print(f"  Max           : {mx:.2f}s")
    print()
    print("  Cost / minute of avatar output (steady-state avg):")
    cost_steady = _cost_per_minute(steady_avg, args.hourly_cost)
    rt_ratio_steady = steady_avg / audio_duration if audio_duration > 0 else float("inf")
    print(f"    ${cost_steady:.5f} / min  (RT-ratio {rt_ratio_steady:.2f}x)")
    print()
    target = 0.02
    if cost_steady < target:
        print(
            f"  TARGET < ${target:.2f}/min: PASSED  (margin: ${target - cost_steady:.5f}/min)"
        )
    else:
        print(
            f"  TARGET < ${target:.2f}/min: FAILED  (over by ${cost_steady - target:.5f}/min)"
        )
    print("=" * 72)


if __name__ == "__main__":
    main()
