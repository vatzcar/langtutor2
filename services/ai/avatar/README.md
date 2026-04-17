# Avatar service (LivePortrait)

Custom Docker service that wraps [KwaiVGI/LivePortrait](https://github.com/KwaiVGI/LivePortrait)
behind a thin FastAPI shim.

## Status

**This container will build, but the shim in `app.py` falls back to a
stub pipeline unless the upstream module paths match what we expect.**
On first run you will almost certainly need to:

1. `docker compose -f docker-compose.ai.yml run --rm --entrypoint bash avatar`
2. Inspect `/app/LivePortrait/` for the current entrypoint (README, `inference.py`,
   `src/live_portrait_pipeline.py`). The project rearranges modules periodically.
3. Adjust `_load_pipeline` and the call in `_run` inside `app.py` accordingly.
4. Download weights. The upstream README has a direct link; place them under
   `/app/checkpoints/` (persisted via the `ai-models` volume).
5. Rebuild: `docker compose -f docker-compose.ai.yml build avatar`.

## Why a custom image?

There is no official public LivePortrait Docker image. `livekit-plugins-avatartalk`
on pypi talks to a hosted SaaS (avatartalk.ai), which is a paid service. To
self-host we run LivePortrait ourselves and either (a) expose an HTTP API that
the backend can poll per utterance, or (b) implement a LiveKit video track
publisher that streams rendered frames.

This shim takes approach (a) as the minimum viable integration.

## Endpoints

- `GET  /health` — liveness.
- `POST /render` — multipart: `audio` (WAV) + `portrait` (JPG/PNG). Returns MP4.
- `WS   /stream` — stub for real-time streaming. Not wired.

## VRAM

About 3.5 GB on an RTX 3070 Ti with the default configuration. Combined with
TTS + STT that's ~7.5 GB on an 8 GB card — tight but feasible. If you hit
CUDA OOM, set `LANGTUTOR_AVATAR_ENABLED=false` on the backend and disable
this service in `docker-compose.ai.yml`.
