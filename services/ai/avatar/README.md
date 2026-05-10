# Avatar — MuseTalk v1.5

Audio-driven talking-head video service.

**Input:** a source video (or image) of a person's face + a WAV of spoken audio
**Output:** MP4 with the source face's lips synchronized to the audio

We swapped out the original LivePortrait shim because LivePortrait alone is
*video-driven* (warps a source image using a driving video's head motion) and
does not produce audio-synchronized lips. MuseTalk (TMElyralab, July 2024)
combines audio feature extraction (Whisper) with a face-editing UNet to
produce lip-sync directly from WAV input.

## Endpoints

| Route            | Verb | Purpose                                   |
|------------------|------|-------------------------------------------|
| `/health`        | GET  | Readiness + weights-present check         |
| `/render`        | POST | One-shot audio + source -> MP4 (~60s per 10s audio) |
| `/stream`        | WS   | Streaming — stub, not implemented yet     |

### `/render` request

Multipart form:
- `audio`: WAV file (16 kHz mono is best; resampled otherwise)
- `source`: MP4 video or still image (jpg/png) of the speaker's face
- `bbox_shift`: optional int (default 0), vertical bbox adjustment in pixels

Response: `video/mp4` bytes.

## First-run weight download

On first container start, `entrypoint.sh` runs MuseTalk's own
`download_weights.sh`, which fetches ~3 GB from HuggingFace, Google Drive,
and pytorch.org into the `ai-models` named volume at `/app/checkpoints`:

```
models/
  musetalkV15/{unet.pth, musetalk.json}
  sd-vae/{config.json, diffusion_pytorch_model.bin}
  whisper/{config.json, pytorch_model.bin, preprocessor_config.json}
  dwpose/dw-ll_ucoco_384.pth
  syncnet/latentsync_syncnet.pt
  face-parse-bisent/{79999_iter.pth, resnet18-5c106cde.pth}
```

Subsequent boots skip the download.

## VRAM

~3.5 GB at inference with v1.5, fp16 path. Comfortable on any 8 GB+ card.

## Building

```bash
docker compose -f docker-compose.ai.yml build avatar
```

~15-25 min first build (CUDA base + torch + mmlab + MuseTalk deps).

## Known caveats

1. **Subprocess per request.** Each `/render` call forks `python -m scripts.inference`
   which reloads models (~5-10 s overhead). For production, refactor to keep
   a persistent worker; MuseTalk's realtime module is a starting point.
2. **mmpose/mmcv pin.** MuseTalk transitively requires the mmlab stack with
   specific versions. The Dockerfile pins `mmcv==2.0.1 / mmdet==3.1.0 /
   mmpose==1.1.0`, known compatible with torch 2.3.1. Bumping torch likely
   needs matching bumps here.
3. **Streaming.** `/stream` WebSocket endpoint returns an error. Real-time
   inference requires persistent worker + chunked encoding — not wired.
4. **Hugging Face mirror.** MuseTalk's download script defaults to
   `hf-mirror.com` (China). The entrypoint patches it to `huggingface.co`
   before first run.

## Dev iteration loop

The server bind-mounts `services/ai/avatar/` into the container at `/app/src`
(see `docker-compose.ai.yml` `volumes:` for the avatar service). This means
you can iterate on `app.py` / `worker.py` without a full image rebuild:

1. Edit locally.
2. Rsync to server: `rsync -av services/ai/avatar/ user@<SERVER_IP>:~/langtutor/services/ai/avatar/`
   (The current dev-server SSH target is in `CLAUDE.md` §4 — it changes on TensorDock instance restart.)
3. Restart the container (no rebuild): `docker compose -f docker-compose.ai.yml restart avatar`
4. Run tests: `docker exec langtutor-avatar pytest /app/src/test_*.py -v`

Only rebuild the image when changing `Dockerfile`, `entrypoint.sh`, or
`requirements.txt`.

> Note: `entrypoint.sh` lives at `/entrypoint.sh` inside the image (not under `/app/src`), so
> editing it on the host requires a full rebuild — the bind-mount only overrides files under `/app/src`.

## Testing

```bash
# After the container is healthy and weights are present
curl -F audio=@sample.wav -F source=@face.jpg \
     http://localhost:8012/render -o out.mp4
```
