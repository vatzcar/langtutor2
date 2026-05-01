# LivePortrait service

Generates idle-motion MP4 loops from a single portrait image using
[KwaiVGI/LivePortrait](https://github.com/KwaiVGI/LivePortrait).

## Endpoints

- `GET /health` — readiness check (weights present?)
- `POST /render` — multipart: `source_image` (PNG/JPG), optional
  `driving_video` (MP4, defaults to built-in idle clip). Returns MP4.

## Running

```bash
docker compose -f docker-compose.ai.yml up liveportrait
```

First boot downloads ~2 GB of weights from HuggingFace. Subsequent
starts reuse the `ai-models` volume.

## VRAM

~4 GB peak at fp16. Runs on the shared GPU alongside STT/TTS/Avatar.
