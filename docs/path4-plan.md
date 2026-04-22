# Path 4 — real-time realistic avatar at `< $0.02/min`

Staged plan for future sessions. Every phase should be executable from a
cold start by reading just this file + `CLAUDE.md`.

---

## 0. Goal

Deliver a **realistic talking-head avatar** that a learner sees during a
LangTutor session, with:

- **Latency** — first-frame under ~500 ms after tutor audio starts.
- **Realism** — natural idle motion (breathing, micro head-sway, blinks)
  between utterances, not a frozen portrait.
- **Unit cost** — `< $0.02/min` of rendered avatar at realistic
  concurrency (`>= 10` simultaneous streams per RTX 4090).

Non-goal: beating closed-source realism. Good enough to be believable
in a 10-minute lesson call is the bar.

---

## 1. Architecture

Two independent pipelines: a slow offline one that produces a per-persona
motion loop once, and a fast online one that paints mouths onto that loop
in real time.

```
OFFLINE (once per persona, admin-triggered)
─────────────────────────────────────────────
persona.image_url (PNG)  ──┐
                           ├──► LivePortrait  ──► persona_idle.mp4
shared "idle motion" clip ─┘     (GPU, ~1–3 min)     (5–10 min loop,
                                                      saved next to portrait)

ONLINE (per session, realtime)
─────────────────────────────────────────────
Gemini text  ──► fish-speech (TTS) ──► audio chunks ──┐
                                                      ├──► MuseTalk worker
persona_idle.mp4 (preloaded, looping) ─────────────┘    (persistent,
                                                         in-memory model)
                                                         │
                                                         ▼
                                           lip-synced frames
                                                         │
                                                         ▼
                                           LiveKit video track  ──► mobile
```

Key property: the slow parts (portrait→idle video, model load) happen
once; steady-state cost is just the MuseTalk forward pass per audio
chunk, shared across concurrent sessions on one GPU.

---

## 2. Phase 1 — LivePortrait service + persona idle-loop generation

**Purpose**: when an admin creates or edits a persona with a portrait,
automatically produce a 5–10 min natural-motion idle MP4 and store its
URL on the persona row. This is the persona's "canvas" for every future
session.

### 2.1 Deliverables

New / modified files (paths are definitive; file names are fixed):

- `services/ai/liveportrait/Dockerfile` — new.
- `services/ai/liveportrait/app.py` — new FastAPI shim with `/render`.
- `services/ai/liveportrait/entrypoint.sh` — new.
- `services/ai/liveportrait/README.md` — new (one page).
- `services/ai/liveportrait/requirements.txt` — new.
- `services/ai/liveportrait/idle_motion_reference.mp4` — checked-in
  driving video of a real human doing idle motion (5–10 min, neutral
  expression, mouth mostly closed). **Large file — use Git LFS or host
  externally and pull in Dockerfile.**
- `docker-compose.ai.yml` — add `liveportrait` service on port 8013.
- `backend/app/config.py` — add `liveportrait_base_url` and
  `idle_loop_enabled` settings.
- `backend/app/models/persona.py` — add nullable `idle_video_url: str`
  column.
- `backend/alembic/versions/<rev>_persona_idle_video.py` — new
  migration.
- `backend/app/schemas/persona.py` — expose `idle_video_url` on reads;
  do **not** accept it on writes (it's server-generated).
- `backend/app/services/persona_service.py` — on `create` / on portrait
  update, enqueue an idle-loop generation job.
- `backend/app/services/liveportrait_service.py` — new module: HTTP
  client for the LivePortrait service + async job runner.
- `backend/app/api/admin/personas.py` — surface job status
  (`idle_loop_status: pending|ready|failed`) in persona read response.
- `admin/src/pages/PersonaManagement.tsx` — show status badge; disable
  "use in session" button while pending.

### 2.2 Tasks in order

1. **Pick a driving motion clip** (~30 min). Requirements: single
   speaker, mouth mostly closed, gentle head sway + blinks, 5–10 min,
   720p minimum, permissively-licensed. Save as
   `idle_motion_reference.mp4`.
2. **Build LivePortrait Docker image** (~2 h). Clone
   `KwaiVGI/LivePortrait` at a pinned ref (start with latest stable
   tag; record it in the Dockerfile ARG). Follow their install; they
   publish prebuilt weights on HuggingFace. FastAPI shim:
   `POST /render (multipart: source_image, driving_video) -> mp4`.
3. **Wire into `docker-compose.ai.yml`** (~15 min) on the
   `ai-network`, port 8013, GPU reservation identical to existing AI
   services. Do **not** put it on the default network.
4. **Alembic migration for `personas.idle_video_url`** (~20 min).
   Nullable, `String(500)` to match `image_url`.
5. **`liveportrait_service.py`** (~2 h). Functions:
   - `render_idle_loop(source_image_path: Path) -> Path` — POSTs to the
     LivePortrait service with the shared driving clip, receives MP4,
     saves to `backend/uploads/idle_loops/<persona_id>.mp4`.
   - `enqueue_idle_loop_render(persona_id: UUID)` — BackgroundTask
     wrapper; updates persona row's `idle_video_url` on success,
     marks a new `idle_loop_status` field (or infers from presence)
     on failure.
6. **Hook into persona create/update** (~30 min). In
   `persona_service.py`, after a successful write where `image_url`
   changed, enqueue the job.
7. **Admin UI status badge** (~1 h). Poll the persona detail endpoint
   until `idle_loop_status == "ready"` or show a "retry" button on
   failed.

**Estimate: ~1 dev day** plus first-run weight-download time.

### 2.3 Verification

- `curl -s http://<server>:8013/health` returns 200 after container is
  up and LivePortrait weights are populated.
- `curl -F source_image=@sample.png -F driving_video=@sample.mp4 \
   http://<server>:8013/render -o out.mp4` produces a playable MP4
  within 3 min wall-time.
- Admin UI: create a new persona with a portrait → within ~3 min the
  status badge flips `pending → ready` and the persona detail page
  shows a preview of the idle loop.
- DB check: `SELECT id, idle_video_url FROM personas WHERE
  idle_video_url IS NOT NULL;` returns the expected rows; the files
  exist under `backend/uploads/idle_loops/`.
- Existing sessions must be **unaffected** when `avatar_enabled=false`;
  there should be no added latency or errors on the happy path.

### 2.4 Risks + mitigations

- **LivePortrait VRAM spikes** beyond ~4 GB on some portraits →
  mitigate by serialising jobs (worker concurrency 1) and letting the
  job queue back up; idle-loop generation isn't latency-critical.
- **Driving clip licence** — don't use YouTube clips without rights.
  Prefer Pexels / Pond5 / a self-recorded clip.
- **Huge checked-in MP4 bloats the repo** — either use Git LFS or host
  the driving clip in the AI-models volume and pull via curl in
  `entrypoint.sh` (preferred: we already do this pattern for MuseTalk
  weights).
- **Admin changes the portrait after ready** — treat as invalidation:
  nuke the old idle MP4 and re-enqueue.

---

## 3. Phase 2 — persistent MuseTalk worker

**Purpose**: eliminate the ~60–90 s subprocess-per-request cost by
keeping the MuseTalk model resident in GPU memory and servicing
requests from an in-process queue.

### 3.1 Deliverables

- `services/ai/avatar/app.py` — refactor: load model once at FastAPI
  startup; new `/render_async` (queued) endpoint; existing `/render`
  kept as a thin wrapper that awaits the queued result.
- `services/ai/avatar/worker.py` — new module: `MuseTalkWorker` class
  that wraps the inference pipeline with preloaded model + whisper
  feature extractor.
- `services/ai/avatar/Dockerfile` — entrypoint no longer launches
  MuseTalk as subprocess; it's a Python import now. Keep all the
  existing install quirks (see `CLAUDE.md` §6).
- `backend/app/services/` — add/extend an avatar client to use the new
  endpoint. No API shape change for upstream callers if we keep
  `/render` synchronous-compatible.

### 3.2 Tasks in order

1. **Read MuseTalk's `scripts/inference.py` end-to-end** (~1 h).
   Identify what's heavy-load (model weights, whisper feature
   extractor, face parser) vs. per-request (bbox, audio features,
   output encoding).
2. **Extract a `MuseTalkWorker` class** (~4 h) that takes the heavy
   load into `__init__` and exposes `infer(audio_path, source_path,
   bbox_shift) -> frames_or_mp4_path`. Verify parity with a
   checksum/visual diff against the subprocess path.
3. **Single-process queue** (~2 h): `asyncio.Queue` of
   `(job_id, audio, source, future)`; a single background task pops
   and runs `worker.infer`. No multi-worker — one GPU, one inference
   process. Concurrency handled at the frame level in Phase 3.
4. **Swap subprocess for in-process call** in `/render` and measure
   latency drop (target: first-frame < 2 s after weights cached).
5. **Preload common personas' idle loops** into the worker's face-parse
   cache on boot — big win for steady-state latency.

**Estimate: ~2 dev days.**

### 3.3 Verification

- Cold start: container reaches `/health == ok` within 2 min.
- `time curl -F audio=@sample.wav -F source=@persona_idle.mp4 \
   http://<server>:8012/render -o out.mp4` — first call: same as
  before. Second call: `< 15 s` for ~10 s of audio.
- Output MP4 is **visually equivalent** to the subprocess output
  (spot-check five frames).
- `nvidia-smi` shows a single persistent python process holding VRAM;
  no per-request reloads.

### 3.4 Risks + mitigations

- **PyTorch model state leaks across calls** (e.g. residual attention
  masks, RNG state) → explicit reset between calls; log first five
  frames for eyeball regression-check.
- **Queue backs up under load** → worker runs one job at a time; if we
  observe queue depth > 3 in practice, revisit (but Phase 3 likely
  obsoletes this concern).
- **Entrypoint complexity** — keep every existing download-weights
  quirk intact; the refactor is purely *what runs after* weights are
  present.

---

## 4. Phase 3 — LiveKit WebRTC real-time video track

**Purpose**: stop returning MP4 files. Start publishing a live video
track into the learner's LiveKit room that the mobile client subscribes
to like any other participant.

### 4.1 Deliverables

- `backend/app/ai/avatar_publisher.py` — new module: connects to the
  LiveKit room as a bot participant, publishes a `VideoTrack` backed
  by frames pulled from the avatar worker.
- `backend/app/ai/agent_worker.py` — when `avatar_enabled`, spin up
  the publisher alongside the voice assistant; pipe TTS audio chunks
  to both the voice track (for the learner to hear) and the avatar
  worker (for lips).
- `services/ai/avatar/worker.py` — extend `infer` → add
  `infer_streaming(audio_chunks, source_loop) -> AsyncIterator[frame]`
  that yields frames as audio streams in.
- `services/ai/avatar/app.py` — replace the stub `/stream` WebSocket
  with a real protocol (binary framing: audio chunk in, frame out) or
  swap it out for a gRPC path if latency calls for it.
- `mobile/lib/screens/` — make sure the session screen is already
  rendering the remote video track (it should be — LiveKit client
  subscribes by default). Test with `avatar_enabled=true`.

### 4.2 Tasks in order

1. **Protocol decision** (~30 min): WebSocket vs. gRPC vs. shared-memory
   between backend worker and avatar service. First pass: WebSocket,
   because the backend and avatar run on the same host and bandwidth
   is not the bottleneck — model inference is. Revisit if profiling
   says otherwise.
2. **Streaming inference** (~1 day). MuseTalk has a `realtime_inference`
   script — use it as the reference implementation, port its chunking
   logic into `MuseTalkWorker.infer_streaming`. Output: 25 fps frames
   (or whatever MuseTalk's native rate is) as raw BGR numpy arrays.
3. **LiveKit VideoTrack publisher** (~1 day). `livekit` SDK has a
   `rtc.VideoSource` you can push frames into. Wire up audio-sync:
   frame N and audio chunk N must arrive at the client together.
4. **Wire into agent worker** (~4 h). Only when `avatar_enabled`; must
   be a no-op when false.
5. **Mobile smoke test** (~2 h). Confirm the client sees the bot
   participant's video track and renders it fullscreen behind the
   subtitle overlay.

**Estimate: ~3 dev days.**

### 4.3 Verification

- Open a session on the mobile app with `avatar_enabled=true`. The
  tutor's face should appear and move naturally in the idle state
  within ~1 s of room-join.
- Speak: TTS fires → tutor's mouth moves in sync with the voice you
  hear. Glass-to-glass lag `< 500 ms` at steady state (stopwatch a
  clap-to-mouth-open test; or inspect LiveKit's `RtcStats`).
- Closing the session disconnects the bot cleanly (no leaked
  publisher, no dangling GPU memory — check `nvidia-smi` returns to
  baseline within 10 s).
- Fallback: with `avatar_enabled=false`, sessions work exactly as they
  do today (audio-only).

### 4.4 Risks + mitigations

- **Audio / video drift** under jitter — use a shared timeline
  (monotonic clock at audio start) and drop frames rather than stall.
- **LiveKit backpressure** if the publisher outruns the network → use
  `VideoSource`'s built-in pacing; if we still hit it, drop to 15 fps.
- **GPU contention** with other concurrent sessions — Phase 4
  benchmarks this; if steady-state per-stream cost is too high, either
  cut fps or temporal-upsample from every-other-frame inference.

---

## 5. Phase 4 — benchmarking + tuning

**Purpose**: prove `< $0.02/min` at realistic concurrency or identify
what needs to change.

### 5.1 Deliverables

- `scripts/bench_avatar_concurrency.py` — new. Spins up N headless
  LiveKit room-participants, each playing a canned audio script into
  the avatar worker; measures per-stream latency, frame rate, and
  total GPU utilisation.
- `docs/avatar-benchmarks.md` — new. Table of (N concurrent,
  first-frame latency, average fps, GPU util%, cost per minute).

### 5.2 Tasks in order

1. **Pick target metrics** (~30 min). Fix definitions: "first-frame
   latency" = time from audio chunk 0 arriving at worker to frame 0
   leaving publisher. "Cost per minute" = (fractional GPU-hour
   consumed) × (hourly $ price of the 4090 instance) ÷ (minutes of
   avatar rendered).
2. **Harness** (~1 day). Python script using LiveKit's Python client
   to join as N fake learners, each streaming a WAV file.
3. **Run the sweep** (~half day). `N = 1, 5, 10, 15, 20, 25`. Plot
   latency-vs-N and fps-vs-N.
4. **Tune** (~1–2 days, highly variable): try fp16 casting, fewer
   denoising steps, lower internal resolution, temporal frame-skip
   with interpolation. Re-run the sweep after each change.
5. **Write up** findings — numbers go into `docs/avatar-benchmarks.md`
   and a short update to this plan if we decide to move the boundary.

**Estimate: ~2–3 dev days.**

### 5.3 Verification

The verification for Phase 4 is the numbers themselves:

- `N = 10`: average cost `< $0.02/min` per stream at steady state.
- `N = 15`: average cost `< $0.015/min` per stream.
- First-frame latency `< 500 ms` up to the chosen concurrency cap.
- Degradation beyond the cap is graceful (frame drops, not hangs).

If we miss the cost target, we do **not** ship Ultra until we either
cut per-stream cost further or raise the plan price.

### 5.4 Risks + mitigations

- **Benchmarks lie** if the fake clients don't match real network
  conditions — run at least one session over a real mobile tether to
  sanity-check.
- **Thermal throttling on TensorDock** at sustained 100% GPU → run
  each sweep for `>= 5 min` to catch it.
- **GPU isn't the bottleneck** — it's the Python GIL or ffmpeg
  encode. If profiling shows that, this phase turns into a rewrite of
  the frame encode path, not a model-tuning exercise.

---

## 6. Out of scope for Path 4

Called out so we don't scope-creep. Any of these come later or never:

- **Hand / full-body gestures.** Talking head only.
- **Multiple avatars in one frame** (e.g. group scene). One persona per
  session.
- **TensorRT engine compilation.** Nice-to-have if Phase 4 says we need
  it; not attempted by default. Introduces deploy friction.
- **Cross-persona motion sharing at runtime.** Every persona gets its
  own idle loop in Phase 1; we don't try to parameterise motion.
- **On-device inference.** Mobile stays as a LiveKit subscriber. No
  Core ML / TFLite.
- **Custom wake-word / always-on listening.** Push-to-talk or
  LiveKit-VAD remains the input model.
- **Multi-language lip-sync quality tuning.** MuseTalk is
  language-agnostic; if some languages look bad, that's a follow-up,
  not part of Path 4.

---

## 7. Open questions (decide with user before each phase)

**Before Phase 1:**

- Driving motion clip — source? (self-recorded vs. stock-library
  licence). Budget for licensing?
- Do we store idle loops on the backend's local disk (current
  `uploads/` convention) or an object store from day one? Local is
  simpler; object store is the "right" answer once there's more than
  one backend pod.
- When an admin updates a persona's portrait, do we invalidate the old
  idle loop synchronously (blocking the update) or lazily (flag as
  stale, re-render in background, keep serving old one until ready)?

**Before Phase 2:**

- OK to remove the `/render` subprocess path entirely, or keep it
  behind a feature flag for a release cycle?
- Single worker vs. multiple — any appetite for two workers even on
  one GPU (lower latency during bursts, higher peak VRAM)?

**Before Phase 3:**

- Protocol for backend↔avatar frames — WebSocket is the easy default;
  does the user want to evaluate gRPC or shared-memory first?
- LiveKit bot participant identity — does it need a distinct
  `identity`/`metadata` so mobile can style the avatar participant
  differently from the learner participant?

**Before Phase 4:**

- Production GPU choice — stay on TensorDock RTX 4090, or benchmark on
  the actual intended prod GPU (A10G? L4? H100 slice)? Cost-per-minute
  is meaningless without the production SKU's hourly price.
- Acceptance criteria if we miss `< $0.02/min` — raise Ultra price,
  cut fps, or kill the avatar entirely for Ultra?

---

## 8. How to resume in a future session

1. Read `CLAUDE.md` first (it points here).
2. Skim this file.
3. `git log --oneline -20` to see what's landed.
4. Pick the earliest unfinished phase.
5. For each task in that phase: implement → verify with the listed
   commands → commit with a focused message.
6. Do not skip phases. Phase 3 depends on Phase 2's persistent worker;
   Phase 4 is meaningless before Phase 3 is shippable.
