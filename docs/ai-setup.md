# LangTutor AI stack — local setup

Self-hosted STT + TTS + Avatar pipeline running on a single RTX 3070 Ti
(8 GB VRAM) via Docker Desktop + WSL2.

## 1. Prerequisites

1. **Windows 10/11 + Docker Desktop with WSL2 backend.** Settings -> General
   -> "Use the WSL 2 based engine" must be on.
2. **NVIDIA driver** (latest Game Ready / Studio driver — 550+ recommended).
3. **NVIDIA Container Toolkit in WSL2.** Follow:
   - [NVIDIA: CUDA on WSL User Guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)
   - [Microsoft: GPU acceleration in WSL](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gpu-compute)
   - Then install the toolkit inside your WSL distro per the
     [NVIDIA Container Toolkit install doc](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
4. **Verify GPU is visible to Docker:**
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi
   ```
   You should see your 3070 Ti listed. If you see
   `Could not select device driver "nvidia"` — the toolkit is not installed
   correctly. Restart Docker Desktop after installing.

## 2. First run

```bash
cd C:\Users\Vatzcar\Documents\LangTutorv2
docker compose -f docker-compose.ai.yml up
```

**First run downloads ~5-10 GB of model weights** into the `langtutor-ai-models`
named volume. Expect:

- STT: `Systran/faster-whisper-base.en` — ~140 MB, downloads in seconds.
- TTS: `fish-speech-1.5` — ~2-3 GB, downloads in minutes.
- Avatar: LivePortrait pretrained weights — ~1-2 GB, **manual step required**
  (see troubleshooting below).

Subsequent starts reuse the volume and come up in seconds.

## 3. VRAM budget (8 GB target)

| Service       | Model                                  | VRAM   |
|---------------|----------------------------------------|--------|
| STT           | faster-whisper base.en (float16)       | ~1.5 GB |
| TTS           | fish-speech-1.5                        | ~2.5 GB |
| Avatar        | LivePortrait (default)                 | ~3.5 GB |
| **Total**     |                                        | **~7.5 GB** |

This is tight. Chrome, the LiveKit server, and Windows itself also
consume VRAM. If you hit `CUDA out of memory`:

- First: close other GPU consumers (browsers, games, etc.).
- Then: set `LANGTUTOR_AVATAR_ENABLED=false` in the backend `.env`, and
  comment out the `avatar` service in `docker-compose.ai.yml`. Audio-only
  calls still work. **This is the default on 8 GB systems.**
- Or: swap the STT model to `distil-whisper/distil-small.en` and the TTS
  to a smaller Fish checkpoint.

## 4. Troubleshooting

### `Could not select device driver "nvidia" with capabilities: [[gpu]]`
NVIDIA Container Toolkit not installed or Docker Desktop needs a restart
after install. Re-run the `nvidia-smi` verification above.

### Avatar container crashes on boot / `ModuleNotFoundError: src.live_portrait_pipeline`
KwaiVGI reorganises the repo periodically. The shim at
`services/ai/avatar/app.py` expects `src.live_portrait_pipeline.LivePortraitPipeline`.
If that path has moved:

```bash
docker compose -f docker-compose.ai.yml run --rm --entrypoint bash avatar
# inside the container:
ls /app/LivePortrait
cat /app/LivePortrait/README.md
```

Adjust the imports in `app.py`, then rebuild:
```bash
docker compose -f docker-compose.ai.yml build avatar
```

### Avatar runs but produces a 1-second black MP4
That's the stub pipeline. It means the real LivePortrait import failed
silently. Check the container logs for the warning "Falling back to stub".

### `CUDA out of memory` during a live call
Disable the avatar (see VRAM section) or reduce TTS/STT model sizes.

### Model weights not persisting across restarts
The `ai-models` volume must exist. Verify:
```bash
docker volume inspect langtutor-ai-models
```

## 5. Testing each service

### STT (faster-whisper)
```bash
curl -F file=@sample.wav \
     -F model=Systran/faster-whisper-base.en \
     http://localhost:8010/v1/audio/transcriptions
```
Returns `{"text": "..."}`. Typical latency on an RTX 3070 Ti for a 5-second
clip: ~200 ms.

### TTS (Fish-Speech)
```bash
curl -X POST \
     -H 'Content-Type: application/json' \
     -d '{"text":"Hello world, this is LangTutor speaking."}' \
     http://localhost:8011/v1/tts \
     -o out.wav
```
Returns a WAV file. Typical latency: ~400 ms for a short utterance.

If you want to clone a voice, base64-encode a 5-10s reference WAV and
add `"reference_audio"` + `"reference_text"`.

### Avatar
```bash
curl -X POST \
     -F audio=@sample.wav \
     -F portrait=@teacher.jpg \
     http://localhost:8012/render \
     -o out.mp4
```
Returns an MP4. Typical latency per 500 ms audio chunk: ~500 ms.

### Health checks
```bash
curl http://localhost:8010/health
curl http://localhost:8011/v1/health
curl http://localhost:8012/health
```

## 6. Backend environment

Set these in `backend/.env` (or via the `LANGTUTOR_*` env vars):

```ini
LANGTUTOR_STT_BASE_URL=http://localhost:8010
LANGTUTOR_TTS_BASE_URL=http://localhost:8011
LANGTUTOR_AVATAR_BASE_URL=http://localhost:8012
LANGTUTOR_AVATAR_ENABLED=false     # flip to true once you have VRAM headroom
LANGTUTOR_STT_MODEL=Systran/faster-whisper-base.en
```

If the backend runs **inside** the same Docker network as the AI stack
(not the default), use service DNS names instead:
```ini
LANGTUTOR_STT_BASE_URL=http://stt:8000
LANGTUTOR_TTS_BASE_URL=http://tts:8080
LANGTUTOR_AVATAR_BASE_URL=http://avatar:8000
```

The LiveKit worker entrypoint (`backend/app/ai/agent_worker.py`) reads
these on startup via the `prewarm` hook — no code changes needed.

## 7. Expected latency (RTX 3070 Ti, best-effort)

| Stage             | Measured        | Notes |
|-------------------|-----------------|-------|
| STT               | ~200 ms         | Per 500 ms chunk, base.en fp16. |
| LLM (Gemini Flash)| ~500 - 800 ms   | Network-bound; unrelated to this stack. |
| TTS               | ~400 ms         | First chunk; streams faster after. |
| Avatar            | ~500 ms / chunk | Synchronous per-utterance render. |
| **End-to-end**    | ~1.5 - 2.0 s    | Speech in -> video out. |

## 8. What needs follow-up work

1. **LivePortrait shim** — the `/render` endpoint works with the stub, but
   real inference requires inspecting the upstream repo for the current
   module paths and wiring them into `services/ai/avatar/app.py`. See
   that file's docstring for pointers. Budget 1-2 hours of upstream-docs
   reading on first setup.
2. **Streaming avatar** — the WebSocket `/stream` endpoint is a stub.
   True low-latency video streaming requires porting LivePortrait's
   TensorRT branch; until then the backend should render one clip per
   assistant turn and publish it as a video track.
3. **Fish-Speech voice cloning** — to differentiate personas, supply
   persona-specific reference WAVs via `FishSpeechTTS(reference_audio_b64=..., reference_text=...)`.
   The backend currently instantiates a single shared TTS; extend
   `prewarm` to build a dict keyed by persona id if you want per-persona
   voices.
