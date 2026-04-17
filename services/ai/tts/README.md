# TTS — Fish-Speech S2

Self-hosted Fish-Speech S2 text-to-speech service for LangTutor.

Fish-Audio does not publish an official Docker image. This container builds
Fish-Speech from source, installs CUDA 12.1 torch wheels, and starts
`python -m tools.api_server` which exposes an OpenAI-ish TTS HTTP API on
port 8080 (mapped to host `:8011`).

## Build

```bash
docker compose -f docker-compose.ai.yml build tts
```

## First run

Weights (~2GB) download from Hugging Face into the `ai-models` named volume.
First boot takes 5-10 minutes on a fast connection; subsequent boots are
seconds.

## Notes / follow-ups

1. The `--compile` flag asks torch to JIT-compile the decoder. This takes
   ~30s on first request of a given text length but roughly doubles throughput
   afterward. Remove it if you hit torch-compile errors on your GPU.
2. The CLI flags on `tools.api_server` drift across fish-speech versions. If
   the container fails to start with flag errors, exec in and run
   `python -m tools.api_server --help` to see the current options.
3. To use a different checkpoint (e.g. the newer S2 release when published),
   override `FISH_SPEECH_CHECKPOINT=fish-speech-1.6` in `docker-compose.ai.yml`.
4. VRAM: ~2.5 GB at idle, up to ~3.5 GB under load with `--compile`.
