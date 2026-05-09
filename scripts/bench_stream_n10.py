"""Streaming benchmark — N=10 concurrent."""

import asyncio
import json
import time

import websockets

AUDIO_PATH = "/tmp/bench_audio.wav"
SOURCE_PATH = "/tmp/bench_source.mp4"
WS_URL = "ws://127.0.0.1:8000/stream"
AUDIO_DURATION = 22.49


async def run_single(run_id):
    with open(AUDIO_PATH, "rb") as f:
        audio_bytes = f.read()

    t0 = time.monotonic()
    try:
        async with websockets.connect(WS_URL, max_size=50 * 1024 * 1024, close_timeout=600) as ws:
            await ws.send(json.dumps({"source_path": SOURCE_PATH, "bbox_shift": 0}))
            await ws.send(audio_bytes)

            frame_count = 0
            first_frame_time = None
            fps = 25
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=600)
                if isinstance(msg, bytes):
                    frame_count += 1
                    if first_frame_time is None:
                        first_frame_time = time.monotonic() - t0
                else:
                    data = json.loads(msg)
                    if data.get("type") == "done":
                        fps = data.get("fps", 25)
                        break
                    if data.get("type") == "error":
                        print("  run %d: ERROR: %s" % (run_id, data.get("error")))
                        return None
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print("  run %d: EXCEPTION after %.1fs: %s" % (run_id, elapsed, exc))
        return None

    elapsed = time.monotonic() - t0
    rtf = elapsed / AUDIO_DURATION
    print("  run %d: elapsed=%.2fs  RTF=%.3f  frames=%d  first_frame=%.2fs" % (
        run_id, elapsed, rtf, frame_count, first_frame_time or 0))
    return {
        "run": run_id,
        "elapsed": round(elapsed, 2),
        "rtf": round(rtf, 3),
        "frames": frame_count,
        "fps": fps,
        "first_frame_s": round(first_frame_time, 2) if first_frame_time else None,
    }


async def main():
    n = 10
    print("=== N=%d concurrent streaming ===" % n)
    t0 = time.monotonic()
    tasks = [asyncio.create_task(run_single(i)) for i in range(n)]
    results = await asyncio.gather(*tasks)
    wall = time.monotonic() - t0
    ok = [r for r in results if r is not None]

    if ok:
        sorted_ok = sorted(ok, key=lambda r: r["elapsed"])
        per_job_delta = sorted_ok[-1]["elapsed"] / len(sorted_ok)
        total_audio = AUDIO_DURATION * len(ok)
        cost_per_min = 0.79 / 60 * (wall / total_audio) * AUDIO_DURATION
        print("  completed: %d/%d" % (len(ok), n))
        print("  wall time: %.1fs" % wall)
        print("  first done: %.1fs  last done: %.1fs" % (sorted_ok[0]["elapsed"], sorted_ok[-1]["elapsed"]))
        print("  per-job delta: %.1fs" % per_job_delta)
        print("  per-job RTF: %.3f" % (per_job_delta / AUDIO_DURATION))
        print("  cost/min: $%.4f" % cost_per_min)
    else:
        print("  ALL FAILED")


asyncio.run(main())
