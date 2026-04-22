# LangTutor — project memory for Claude

Persistent anchor for future sessions. Keep this dense and scannable. Update
when architecture or deployment facts change; leave ephemeral task state out.

## 1. What LangTutor is

LangTutor is a freemium AI language-tutoring app. Learners talk to a
realistic AI tutor (voice + talking-head avatar) in their target language.
Sessions are graded against CEFR (A0–C2), progress is tracked, and a paid
Ultra plan ($199/year) unlocks unlimited minutes and the realistic avatar.
A Flutter mobile app is the learner surface; a React admin console is the
operator surface; a FastAPI backend orchestrates auth, sessions, plans, and
LiveKit agents that bridge to self-hosted STT / TTS / Avatar GPU services.

## 2. Tech stack

- **Mobile**: Flutter 3.x (`mobile/`). Uses LiveKit client for realtime
  voice/video. State via providers.
- **Admin**: React 18 + Vite + TypeScript + Tailwind (`admin/`). Pages
  for users, personas, plans, languages, reports/logs.
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy 2 (async) + Alembic +
  Pydantic v2 (`backend/`). Postgres 16 is the system of record.
- **Realtime orchestration**: LiveKit server + livekit-agents Python
  worker. The worker runs inside the backend process (`agent_worker.py`)
  and wires Gemini LLM + remote STT/TTS/Avatar plugins into a
  `VoiceAssistant`.
- **AI stack** (`services/ai/` + `docker-compose.ai.yml`):
  - `stt` — speaches (faster-whisper base.en, fp16), OpenAI-compatible HTTP
  - `tts` — fish-speech v1.5 (built from source, no official image)
  - `avatar` — MuseTalk v1.5 (built from source; audio-driven lip-sync)
- **LLM**: Google Gemini (`gemini-1.5-flash` default), called via
  `google-generativeai`. Not self-hosted.

## 3. Repo layout

```
backend/                 FastAPI service
  app/
    ai/                  LiveKit-agents worker + plugins (stt/tts/gemini)
    api/admin/           Admin REST endpoints
    api/mobile/          Mobile REST endpoints
    api/internal.py      Internal endpoints the agent worker calls
    services/            Business logic (auth, plan, session, persona, …)
    models/              SQLAlchemy ORM
    schemas/             Pydantic request/response models
    utils/permissions.py Admin RBAC constants + helpers
    config.py            Pydantic settings (LANGTUTOR_* env vars)
  alembic/               DB migrations
  scripts/               One-off migration + seed scripts
admin/src/               React admin SPA
  constants/permissions.ts  Mirror of backend permissions (keep in sync)
  pages/                 One page per admin section
mobile/lib/              Flutter app (screens, providers, services)
services/ai/
  tts/                   fish-speech Dockerfile + entrypoint
  avatar/                MuseTalk Dockerfile + entrypoint + FastAPI shim
docs/                    Operator/setup docs + Path 4 plan (this session)
docker-compose.yml       Local dev: db + backend + livekit
docker-compose.ai.yml    GPU AI stack (stt/tts/avatar) — separate file
REQUIREMENTS.md          Product spec. Source of truth for features.
```

## 4. Deployed environment

Dev / pilot on TensorDock, **RTX 4090 (24 GB VRAM)**, Ubuntu 22.04.

- SSH: `ssh -i $USERPROFILE/.ssh/id_ed25519 user@38.224.253.71`
- Public IP `38.224.253.71`, plain HTTP, **no domain yet**.
- All containers healthy at last check.

| Container           | Image / build              | Host port     | Internal |
| ------------------- | -------------------------- | ------------- | -------- |
| langtutor-db        | postgres:16-alpine         | 5432 (bound)  | 5432     |
| langtutor-backend   | `./backend` Dockerfile     | 8001          | 8000     |
| langtutor-livekit   | livekit/livekit-server     | 7880 / 7881   | 7880/1   |
| langtutor-stt       | ghcr.io/speaches-ai/speaches:latest-cuda | 8010 | 8000 |
| langtutor-tts       | `./services/ai/tts`        | 8011          | 8080     |
| langtutor-avatar    | `./services/ai/avatar`     | 8012          | 8000     |

Networks:
- `langtutor_default` — db + backend + livekit.
- `langtutor-ai-network` — stt + tts + avatar.
- **Backend is attached to both** so it can resolve `stt`, `tts`, `avatar`
  by hostname. This dual-attach is done via a manual edit to the server's
  `docker-compose.yml`; it's **not** in the repo (see §6).

## 5. Key env vars

Stored outside the repo. Names only — never commit values.

`backend/.env` (on server):
- `LANGTUTOR_DATABASE_URL`
- `LANGTUTOR_SECRET_KEY`
- `LANGTUTOR_GEMINI_API_KEY`
- `LANGTUTOR_GEMINI_MODEL` (=`gemini-1.5-flash`)
- `LANGTUTOR_LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`
- `LANGTUTOR_STT_BASE_URL` / `TTS_BASE_URL` / `AVATAR_BASE_URL`
- `LANGTUTOR_AVATAR_ENABLED` (=`true` on server)

`.env.prod` (server-only, compose interpolation):
- `DB_PASSWORD` — substituted into `docker-compose.yml` postgres env.

Prefix `LANGTUTOR_` is required — see `backend/app/config.py`.

## 6. Architecture decisions / quirks already baked in

Don't re-litigate these without strong reason; each has a scar behind it.

- **bcrypt pinned `<4.1`** in `backend/pyproject.toml`. passlib's startup
  probe hashes a long sentinel string; bcrypt 4.1+ enforces the 72-byte
  input limit and raises, breaking *any* hash path. Keep the pin until
  we move off passlib.
- **fish-speech pinned to `v1.5.0`** in `services/ai/tts/Dockerfile`
  (build arg `FISH_REF=v1.5.0`). Newer refs have shifted the
  `tools.api_server` entry.
- **MuseTalk install is a minefield.** `services/ai/avatar/Dockerfile`
  carries all of these together — removing any one breaks the build:
  1. Torch 2.3.1 + CUDA 12.1 wheels installed *before* MuseTalk's own
     `requirements.txt` so it doesn't pull a CPU build.
  2. `mmcv==2.2.0` from OpenMMLab's prebuilt-wheel index for
     `cu121/torch2.3` (2.0.x can't build from source under modern pip).
  3. `chumpy==0.70` installed with `--no-build-isolation` because its
     `setup.py` imports `numpy` at build time.
  4. `mmdet==3.3.0` — but the package hard-asserts `mmcv<2.2.0`, so
     the Dockerfile `sed`s `mmcv_maximum_version` to `"2.3.0"`.
  5. MuseTalk's `download_weights.sh` is patched at runtime in
     `entrypoint.sh`: rewrites `hf-mirror.com`→`huggingface.co`, neuters
     the `huggingface_hub[cli]` upgrade that would break tokenizers,
     strips `--id` from gdown calls, and `set -euo pipefail`.
  6. Post-download block re-fetches **four JSON configs** that upstream's
     `hf download --include "a" "b"` drops (only last pattern wins) —
     `sd-vae/config.json`, `whisper/config.json`,
     `musetalkV15/musetalk.json`, `musetalk/musetalk.json`.
  7. face-parse-bisent weight (GDrive) has a retry block using `gdown`
     directly if upstream's call silently failed.
- **`LANGTUTOR_AVATAR_ENABLED`** is the feature gate. The tutor agent
  (`backend/app/ai/agent_worker.py`) reads it and only calls the avatar
  service when true. Default is off.
- **Server's `docker-compose.yml` has diverged from the repo's.** On the
  server it has: bind-mount of `./backend` into the backend container,
  `${DB_PASSWORD}` interpolation for postgres, and a second network entry
  attaching backend to `langtutor-ai-network`. The repo's version is
  still the minimal dev-laptop compose. **Do not try to reconcile yet** —
  we'll fold this in when we productionise. When editing compose locally,
  be aware the server's file is the authoritative one for prod.
- **docker-compose.ai.yml's `avatar` service still has env vars named
  `LIVEPORTRAIT_*`** even though the service is now MuseTalk. Harmless
  (shim ignores them) but worth cleaning up when touching that file.

## 7. Known limits / stubs

- `services/ai/avatar/app.py` **`/stream` WebSocket is a stub** — it
  accepts and immediately returns `streaming_not_implemented`. Path 4
  Phase 3 replaces this with a real streaming track.
- Avatar inference is **subprocess-per-request** (`python -m
  scripts.inference`). ~60–90 s wall time per 10 s of audio on a 4090
  because of model load cost. Path 4 Phase 2 makes this a persistent
  worker.
- **LivePortrait service does not exist yet** — planned for Path 4
  Phase 1 (per-persona idle-loop pre-render).
- Repo's `docker-compose.yml` is dev-only; see §6.

## 8. Pointers — where to read first

- **Tutor agent behaviour** → `backend/app/ai/agent_worker.py` +
  `backend/app/ai/tutor_agent.py` + `backend/app/ai/prompt_templates.py`.
- **STT/TTS/Avatar plugin wiring** → `backend/app/ai/stt_plugin.py`,
  `tts_plugin.py`, `gemini_plugin.py`.
- **Admin RBAC** → `backend/app/utils/permissions.py` and
  `admin/src/constants/permissions.ts` (mirror — keep in sync).
- **Session lifecycle + CEFR scoring** →
  `backend/app/services/session_service.py` +
  `backend/app/ai/cefr_assessor.py`.
- **Subscriptions / plans** → `backend/app/services/plan_service.py`
  and `subscription_service.py`.
- **Mobile entrypoint** → `mobile/lib/app.dart` and
  `mobile/lib/main.dart`; LiveKit session UI under `mobile/lib/screens/`.
- **Avatar service shim** → `services/ai/avatar/app.py` (what runs
  when backend POSTs to `:8012/render`).
- **Ops docs** → `docs/ai-setup.md`, `docs/production-setup.md`.

## 9. Business constraints

- **Ultra plan is $199/year (~$16.58/month).** Unit economics must clear.
- Target **avatar cost `< $0.02/min`** at realistic concurrency. No
  closed-source realtime realistic provider hits this; only self-hosting
  with shared-GPU concurrency does. This is why the architecture is
  self-hosted end-to-end on the AI side.
- Gemini calls are small text — dwarfed by avatar GPU time — and stay on
  the managed API for now.

## 10. Current focus / next task

**Path 4 Phase 1 per `docs/path4-plan.md`.**

Path 4 = per-persona pre-rendered idle loop (LivePortrait) + runtime
real-time MuseTalk lip-sync overlaid on the loop. Expected ~15–20
concurrent streams on one RTX 4090, amortizing to ~$0.01/min at 10+
concurrent. See `docs/path4-plan.md` for staged plan with
deliverables/verification per phase.
