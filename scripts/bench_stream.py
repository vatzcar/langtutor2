"""Streaming WebSocket benchmark for avatar service.

Measures RTF (Real-Time Factor) for the /stream endpoint
vs the batch /render endpoint.
"""

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
    async with websockets.connect(WS_URL, max_size=50 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"source_path": SOURCE_PATH, "bbox_shift": 0}))
        await ws.send(audio_bytes)

        frame_count = 0
        first_frame_time = None
        fps = 25
        while True:
            msg = await ws.recv()
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

    elapsed = time.monotonic() - t0
    rtf = elapsed / AUDIO_DURATION
    return {
        "run": run_id,
        "elapsed": round(elapsed, 2),
        "rtf": round(rtf, 3),
        "frames": frame_count,
        "fps": fps,
        "first_frame_s": round(first_frame_time, 2) if first_frame_time else None,
    }


async def run_concurrent(n):
    tasks = [asyncio.create_task(run_single(i)) for i in range(n)]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


async def main():
    print("=== Warmup run ===")
    warmup = await run_single(0)
    if warmup:
        print("  warmup: elapsed=%(elapsed)ss  RTF=%(rtf)s  frames=%(frames)s  first_frame=%(first_frame_s)ss" % warmup)
    else:
        print("  warmup FAILED")
        return

    print()
    print("=== N=1 baseline (3 runs) ===")
    baselines = []
    for i in range(3):
        r = await run_single(i)
        if r:
            baselines.append(r)
            print("  run %(run)d: elapsed=%(elapsed)ss  RTF=%(rtf)s  frames=%(frames)s  first_frame=%(first_frame_s)ss" % r)

    if baselines:
        avg_rtf = sum(r["rtf"] for r in baselines) / len(baselines)
        avg_elapsed = sum(r["elapsed"] for r in baselines) / len(baselines)
        print("  AVG: elapsed=%.2fs  RTF=%.3f" % (avg_elapsed, avg_rtf))

    for n in [5, 10]:
        print()
        print("=== N=%d concurrent ===" % n)
        t0 = time.monotonic()
        results = await run_concurrent(n)
        wall = time.monotonic() - t0
        if results:
            avg_rtf = sum(r["rtf"] for r in results) / len(results)
            max_rtf = max(r["rtf"] for r in results)
            min_elapsed = min(r["elapsed"] for r in results)
            max_elapsed = max(r["elapsed"] for r in results)
            total_audio = AUDIO_DURATION * len(results)
            cost_per_min = 0.79 / 60 * (wall / total_audio) * AUDIO_DURATION
            throughput = total_audio / wall
            print("  completed: %d/%d" % (len(results), n))
            print("  wall time: %.1fs" % wall)
            print("  per-request: min=%.1fs  max=%.1fs" % (min_elapsed, max_elapsed))
            print("  RTF: avg=%.3f  max=%.3f" % (avg_rtf, max_rtf))
            print("  throughput: %.2fs audio/s wall" % throughput)
            print("  cost/min: $%.4f" % cost_per_min)
        else:
            print("  ALL FAILED")


asyncio.run(main())
