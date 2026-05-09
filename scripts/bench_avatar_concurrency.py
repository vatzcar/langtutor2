#!/usr/bin/env python3
"""Phase 4 — avatar concurrency benchmark harness.

Measures MuseTalk render throughput against the avatar service's HTTP API
and derives cost-per-minute at various concurrency levels.

Metrics
-------
- **Real-time factor (RTF)**: render_time / audio_duration.
  RTF < 1 means faster than real-time.
- **Max concurrent streams**: floor(1 / RTF).  The serial worker can
  sustain this many simultaneous streams without falling behind.
- **Cost per minute**: RTF × (gpu_hourly_rate / 60).
- **First-job latency**: wall-clock time from request to MP4 for the
  first job in a concurrent batch (proxy for first-frame latency until
  Phase 3 streaming lands).

Usage
-----
    # Single-stream baseline (generates a 10 s sine-wave WAV automatically)
    python scripts/bench_avatar_concurrency.py \\
        --avatar-url http://localhost:8012 \\
        --source sample_portrait.png \\
        --audio-duration 10

    # Full sweep (N = 1,5,10,15,20,25)
    python scripts/bench_avatar_concurrency.py \\
        --avatar-url http://localhost:8012 \\
        --source idle_loop.mp4 \\
        --audio-duration 10 \\
        --sweep

    # Custom concurrency levels
    python scripts/bench_avatar_concurrency.py \\
        --avatar-url http://localhost:8012 \\
        --source idle_loop.mp4 \\
        --sweep --levels 1 5 10

Prerequisites
-------------
- pip install httpx numpy  (both already in the backend's deps)
- Avatar service must be running and healthy
- nvidia-smi on PATH for GPU utilisation sampling (optional)
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import math
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("bench")

DEFAULT_LEVELS = [1, 5, 10, 15, 20, 25]
DEFAULT_GPU_HOURLY_RATE = 0.74  # TensorDock RTX 4090 $/hr (as of 2025-Q1)


# ------------------------------------------------------------------ helpers


def generate_sine_wav(duration_s: float, sample_rate: int = 16000, freq: float = 440.0) -> bytes:
    """Generate a mono 16-bit PCM WAV in memory."""
    n_samples = int(sample_rate * duration_s)
    amplitude = 16000
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        val = int(amplitude * math.sin(2 * math.pi * freq * t))
        samples.append(struct.pack("<h", max(-32768, min(32767, val))))
    pcm = b"".join(samples)

    buf = io.BytesIO()
    # RIFF header
    data_size = len(pcm)
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16))
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm)
    return buf.getvalue()


def sample_gpu_utilisation() -> Optional[dict]:
    """Query nvidia-smi for GPU utilisation and memory. Returns None if unavailable."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            timeout=5,
            text=True,
        )
        parts = [p.strip() for p in out.strip().split(",")]
        if len(parts) >= 6:
            return {
                "gpu_util_pct": float(parts[0]),
                "mem_util_pct": float(parts[1]),
                "mem_used_mb": float(parts[2]),
                "mem_total_mb": float(parts[3]),
                "temp_c": float(parts[4]),
                "power_w": float(parts[5]),
            }
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


@dataclass
class JobResult:
    job_id: str
    submit_time: float
    ready_time: float
    wall_s: float
    status: str
    error: Optional[str] = None


@dataclass
class BenchResult:
    concurrency: int
    audio_duration_s: float
    jobs: list[JobResult] = field(default_factory=list)
    gpu_samples: list[dict] = field(default_factory=list)
    sweep_wall_s: float = 0.0

    @property
    def successful_jobs(self) -> list[JobResult]:
        return [j for j in self.jobs if j.status == "ready"]

    @property
    def first_job_latency_s(self) -> float:
        ok = self.successful_jobs
        if not ok:
            return float("inf")
        return min(j.wall_s for j in ok)

    @property
    def avg_job_time_s(self) -> float:
        ok = self.successful_jobs
        if not ok:
            return float("inf")
        return sum(j.wall_s for j in ok) / len(ok)

    @property
    def total_rendered_minutes(self) -> float:
        return len(self.successful_jobs) * self.audio_duration_s / 60.0

    @property
    def rtf(self) -> float:
        """Real-time factor based on average single-job render time."""
        ok = self.successful_jobs
        if not ok:
            return float("inf")
        return self.avg_job_time_s / self.audio_duration_s

    @property
    def max_concurrent(self) -> int:
        if self.rtf <= 0 or self.rtf == float("inf"):
            return 0
        return int(1.0 / self.rtf)

    def cost_per_min(self, gpu_rate: float) -> float:
        if self.rtf == float("inf"):
            return float("inf")
        return self.rtf * (gpu_rate / 60.0)

    @property
    def avg_gpu_util(self) -> Optional[float]:
        vals = [s["gpu_util_pct"] for s in self.gpu_samples if "gpu_util_pct" in s]
        return sum(vals) / len(vals) if vals else None

    @property
    def avg_power_w(self) -> Optional[float]:
        vals = [s["power_w"] for s in self.gpu_samples if "power_w" in s]
        return sum(vals) / len(vals) if vals else None


# ----------------------------------------------------------- benchmark core


async def check_health(client: httpx.AsyncClient, url: str) -> dict:
    resp = await client.get(f"{url}/health", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"avatar service not ready: {data}")
    return data


async def submit_and_poll(
    client: httpx.AsyncClient,
    url: str,
    audio_bytes: bytes,
    source_bytes: bytes,
    source_filename: str,
    poll_interval: float = 0.5,
    timeout: float = 600,
) -> JobResult:
    """Submit a render_async job and poll until completion."""
    t0 = time.monotonic()

    files = {
        "audio": ("test.wav", audio_bytes, "audio/wav"),
        "source": (source_filename, source_bytes, "application/octet-stream"),
    }
    resp = await client.post(f"{url}/render_async", files=files, data={"bbox_shift": "0"}, timeout=60)
    resp.raise_for_status()
    job_id = resp.json()["job_id"]

    deadline = t0 + timeout
    while time.monotonic() < deadline:
        await asyncio.sleep(poll_interval)
        r = await client.get(f"{url}/jobs/{job_id}", timeout=30)
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            if "video" in ct:
                wall = time.monotonic() - t0
                # Cleanup server-side temp files
                try:
                    await client.delete(f"{url}/jobs/{job_id}", timeout=10)
                except Exception:
                    pass
                return JobResult(job_id=job_id, submit_time=t0, ready_time=t0 + wall, wall_s=wall, status="ready")
            body = r.json()
            if body.get("status") == "failed":
                wall = time.monotonic() - t0
                return JobResult(job_id=job_id, submit_time=t0, ready_time=t0 + wall, wall_s=wall, status="failed", error=body.get("error"))
        elif r.status_code >= 500:
            body = r.json() if "json" in r.headers.get("content-type", "") else {}
            wall = time.monotonic() - t0
            return JobResult(job_id=job_id, submit_time=t0, ready_time=t0 + wall, wall_s=wall, status="failed", error=body.get("error", f"HTTP {r.status_code}"))

    wall = time.monotonic() - t0
    return JobResult(job_id=job_id, submit_time=t0, ready_time=t0 + wall, wall_s=wall, status="failed", error="timeout")


async def gpu_sampler(result: BenchResult, stop_event: asyncio.Event, interval: float = 1.0) -> None:
    """Sample GPU stats in the background while benchmark runs."""
    loop = asyncio.get_event_loop()
    while not stop_event.is_set():
        sample = await loop.run_in_executor(None, sample_gpu_utilisation)
        if sample:
            result.gpu_samples.append(sample)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


async def run_concurrency_level(
    url: str,
    n: int,
    audio_bytes: bytes,
    source_bytes: bytes,
    source_filename: str,
    audio_duration_s: float,
) -> BenchResult:
    """Submit n concurrent render jobs and collect results."""
    result = BenchResult(concurrency=n, audio_duration_s=audio_duration_s)
    stop_gpu = asyncio.Event()

    async with httpx.AsyncClient() as client:
        await check_health(client, url)

        gpu_task = asyncio.create_task(gpu_sampler(result, stop_gpu))
        t0 = time.monotonic()

        tasks = [
            submit_and_poll(client, url, audio_bytes, source_bytes, source_filename)
            for _ in range(n)
        ]
        jobs = await asyncio.gather(*tasks)
        result.sweep_wall_s = time.monotonic() - t0

        stop_gpu.set()
        await gpu_task

    result.jobs = list(jobs)
    return result


# --------------------------------------------------------------- reporting


def format_table(results: list[BenchResult], gpu_rate: float) -> str:
    """Format results as a markdown table."""
    lines = [
        "| N | Avg render (s) | RTF | First-job (s) | Max concurrent | Cost/min ($) | GPU util (%) | Wall time (s) | OK/Total |",
        "|---|----------------|-----|---------------|----------------|-------------|-------------|--------------|----------|",
    ]
    for r in results:
        gpu_str = f"{r.avg_gpu_util:.0f}" if r.avg_gpu_util is not None else "n/a"
        cpm = r.cost_per_min(gpu_rate)
        cpm_str = f"{cpm:.4f}" if cpm != float("inf") else "n/a"
        ok = len(r.successful_jobs)
        lines.append(
            f"| {r.concurrency} "
            f"| {r.avg_job_time_s:.1f} "
            f"| {r.rtf:.3f} "
            f"| {r.first_job_latency_s:.1f} "
            f"| {r.max_concurrent} "
            f"| {cpm_str} "
            f"| {gpu_str} "
            f"| {r.sweep_wall_s:.1f} "
            f"| {ok}/{r.concurrency} |"
        )
    return "\n".join(lines)


def format_summary(results: list[BenchResult], gpu_rate: float, audio_dur: float) -> str:
    """Human-readable summary block."""
    parts = [
        f"GPU hourly rate: ${gpu_rate:.2f}/hr",
        f"Audio duration per job: {audio_dur:.1f} s",
        "",
    ]

    baseline = next((r for r in results if r.concurrency == 1), None)
    if baseline and baseline.successful_jobs:
        parts.append(f"Baseline RTF (N=1): {baseline.rtf:.3f}")
        parts.append(f"  → renders {1/baseline.rtf:.1f}× faster than real-time")
        parts.append(f"  → theoretical max concurrent streams: {baseline.max_concurrent}")
        parts.append(f"  → cost at N=1: ${baseline.cost_per_min(gpu_rate):.4f}/min")
        parts.append("")

    for target_n, target_cost in [(10, 0.02), (15, 0.015)]:
        r = next((r for r in results if r.concurrency == target_n), None)
        if r and r.successful_jobs:
            cpm = r.cost_per_min(gpu_rate)
            status = "PASS" if cpm < target_cost else "FAIL"
            parts.append(f"N={target_n}: cost ${cpm:.4f}/min (target <${target_cost:.3f}) [{status}]")

    return "\n".join(parts)


def write_benchmarks_doc(results: list[BenchResult], gpu_rate: float, audio_dur: float, outpath: Path) -> None:
    table = format_table(results, gpu_rate)
    summary = format_summary(results, gpu_rate, audio_dur)

    baseline = next((r for r in results if r.concurrency == 1), None)

    gpu_section = ""
    if results and results[0].gpu_samples:
        s = results[0].gpu_samples[0]
        gpu_section = f"""
## GPU environment

| Key | Value |
|-----|-------|
| Memory total | {s.get('mem_total_mb', 'n/a')} MB |
| FP16 | yes (MuseTalk default) |
| Pricing | ${gpu_rate:.2f}/hr |
"""

    content = f"""# Avatar concurrency benchmarks

Generated by `scripts/bench_avatar_concurrency.py`.

## Summary

```
{summary}
```

## Method

Each benchmark level submits N concurrent render jobs to the avatar
service's `/render_async` endpoint. The service processes jobs serially
(single GPU, one inference at a time via `MuseTalkWorker`). Wall time
and per-job latency are measured from the client side.

**Definitions:**

- **RTF** (real-time factor): `render_time / audio_duration`. RTF < 1
  means the GPU renders faster than real-time.
- **Max concurrent**: `floor(1 / RTF)`. How many simultaneous streams
  one GPU can sustain without falling behind.
- **Cost/min**: `RTF × (GPU $/hr) / 60`. Per-stream cost at steady
  state, assuming 100% utilisation.
- **First-job latency**: wall time for the first completed job in a
  batch. Proxy for first-frame latency until Phase 3 streaming lands.
{gpu_section}
## Results

{table}

## Verification

| Target | Threshold | Measured | Status |
|--------|-----------|----------|--------|
"""

    for target_n, target_cost, label in [(10, 0.02, "N=10 cost/min"), (15, 0.015, "N=15 cost/min")]:
        r = next((r for r in results if r.concurrency == target_n), None)
        if r and r.successful_jobs:
            cpm = r.cost_per_min(gpu_rate)
            status = "PASS" if cpm < target_cost else "FAIL"
            content += f"| {label} | <${target_cost:.3f} | ${cpm:.4f} | {status} |\n"
        else:
            content += f"| {label} | <${target_cost:.3f} | not tested | - |\n"

    # First-frame latency check (proxy)
    if baseline and baseline.successful_jobs:
        ffl = baseline.first_job_latency_s
        status = "PASS" if ffl < 30 else "FAIL"
        content += f"| First-job latency (N=1) | <30 s (batch proxy) | {ffl:.1f} s | {status} |\n"

    content += """
## Notes

- The avatar worker processes one job at a time (serial). Concurrency
  N > 1 means N jobs queued; total wall time scales linearly.
- The cost metric assumes the GPU is fully dedicated to avatar rendering.
  In production, STT and TTS share the same GPU — effective avatar
  capacity is lower.
- Phase 3 (streaming inference) will enable true first-frame latency
  measurement. The "first-job latency" here includes full-video encode
  time and is not comparable to the <500 ms target for streaming.
- Thermal throttling may affect sustained workloads. Each sweep level
  runs long enough to observe throttling effects.
"""

    outpath.write_text(content, encoding="utf-8")


# -------------------------------------------------------------------- main


async def main() -> None:
    parser = argparse.ArgumentParser(description="Avatar concurrency benchmark")
    parser.add_argument("--avatar-url", default="http://localhost:8012", help="Avatar service base URL")
    parser.add_argument("--source", required=True, help="Source image or video file (persona portrait / idle loop)")
    parser.add_argument("--audio", help="WAV audio file. If omitted, a sine-wave is generated.")
    parser.add_argument("--audio-duration", type=float, default=10.0, help="Duration of generated audio in seconds (ignored if --audio is set)")
    parser.add_argument("--sweep", action="store_true", help="Run full concurrency sweep")
    parser.add_argument("--levels", nargs="+", type=int, default=None, help="Custom concurrency levels (default: 1 5 10 15 20 25)")
    parser.add_argument("--gpu-rate", type=float, default=DEFAULT_GPU_HOURLY_RATE, help="GPU hourly rate in $/hr")
    parser.add_argument("--output", default="docs/avatar-benchmarks.md", help="Output markdown file")
    parser.add_argument("--warmup", action="store_true", help="Run a single warmup job before the sweep")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(name)s %(message)s")

    source_path = Path(args.source)
    if not source_path.exists():
        logger.error("source file not found: %s", source_path)
        sys.exit(1)
    source_bytes = source_path.read_bytes()
    source_filename = source_path.name

    if args.audio:
        audio_path = Path(args.audio)
        if not audio_path.exists():
            logger.error("audio file not found: %s", audio_path)
            sys.exit(1)
        audio_bytes = audio_path.read_bytes()
        # Estimate duration from WAV header
        if len(audio_bytes) > 44:
            sr = struct.unpack_from("<I", audio_bytes, 24)[0]
            data_size = struct.unpack_from("<I", audio_bytes, 40)[0]
            audio_duration = data_size / (sr * 2)  # 16-bit mono
        else:
            audio_duration = args.audio_duration
    else:
        audio_duration = args.audio_duration
        logger.info("generating %g s sine-wave WAV", audio_duration)
        audio_bytes = generate_sine_wav(audio_duration)

    levels = args.levels or (DEFAULT_LEVELS if args.sweep else [1])

    logger.info("avatar service: %s", args.avatar_url)
    logger.info("source: %s (%d bytes)", source_filename, len(source_bytes))
    logger.info("audio: %g s (%d bytes)", audio_duration, len(audio_bytes))
    logger.info("levels: %s", levels)
    logger.info("GPU rate: $%.2f/hr", args.gpu_rate)

    # Health check
    async with httpx.AsyncClient() as client:
        health = await check_health(client, args.avatar_url)
        logger.info("health: %s", json.dumps(health))

    # Optional warmup
    if args.warmup:
        logger.info("running warmup job...")
        warmup = await run_concurrency_level(
            args.avatar_url, 1, audio_bytes, source_bytes, source_filename, audio_duration,
        )
        if warmup.successful_jobs:
            logger.info("warmup done: %.1f s", warmup.successful_jobs[0].wall_s)
        else:
            logger.warning("warmup failed: %s", warmup.jobs[0].error if warmup.jobs else "no jobs")

    # Run sweep
    results: list[BenchResult] = []
    for n in levels:
        logger.info("--- N=%d ---", n)
        r = await run_concurrency_level(
            args.avatar_url, n, audio_bytes, source_bytes, source_filename, audio_duration,
        )
        results.append(r)

        ok = len(r.successful_jobs)
        logger.info(
            "N=%d: %d/%d ok, avg=%.1fs, RTF=%.3f, cost=$%.4f/min, wall=%.1fs",
            n, ok, n, r.avg_job_time_s, r.rtf,
            r.cost_per_min(args.gpu_rate), r.sweep_wall_s,
        )
        if r.avg_gpu_util is not None:
            logger.info("  GPU util: %.0f%%", r.avg_gpu_util)

    # Print table
    print()
    print(format_table(results, args.gpu_rate))
    print()
    print(format_summary(results, args.gpu_rate, audio_duration))

    # Write docs
    outpath = Path(args.output)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    write_benchmarks_doc(results, args.gpu_rate, audio_duration, outpath)
    logger.info("wrote %s", outpath)


if __name__ == "__main__":
    asyncio.run(main())
