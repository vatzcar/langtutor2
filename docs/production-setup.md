# LangTutor — Production deployment runbook

**Audience:** me (Claude) executing a deploy on a fresh server, plus a human
operator following along. Every command is copy-paste-ready. Every phase ends
with a **Verify** block — if verification fails, fix before moving on.

**Target host:** bare-metal Ubuntu 22.04 LTS with an NVIDIA RTX 3090 (24 GB).
**Target scale:** pilot / small production — up to ~5 concurrent video-avatar
sessions, ~15 concurrent audio-only sessions.

---

## 0. Architecture at a glance

```
            ┌────────────────── Internet ────────────────────┐
            │                                                │
    api.<domain>                                    livekit.<domain>
   admin.<domain>                                         (UDP 7881-7882)
            │                                                │
            ▼                                                ▼
   ┌─────────────────┐  TLS terminated by Caddy  ┌────────────────────┐
   │      Caddy      │◀────────────────────────▶│   LiveKit server   │
   │    :80/:443     │                          │ WebRTC SFU:7880    │
   └────────┬────────┘                          └────────────────────┘
            │
            │ proxies /api/* → backend:8001
            │ proxies /      → admin static
            ▼
   ┌─────────────────┐      ┌──────────────────────────────────────────┐
   │  FastAPI back   │─────▶│  Postgres (docker volume)                │
   │  gunicorn:8001  │      └──────────────────────────────────────────┘
   │   (docker)      │
   └─────────┬───────┘
             │ internal HTTP
             ├──────▶  STT   (speaches :8010)    │
             ├──────▶  TTS   (fish-speech :8011) │  ── all on GPU
             └──────▶  Avatar (liveportrait:8012) │
                                                 (localhost-only binds)
```

**What lives where:**

| Service         | Container name            | Host port           | GPU  | Public?                    |
|-----------------|---------------------------|---------------------|------|----------------------------|
| Caddy           | caddy                     | 80, 443             | no   | **yes**                    |
| Backend         | langtutor-backend         | 127.0.0.1:8001      | no   | no (via Caddy)             |
| Postgres        | langtutor-db              | 127.0.0.1:5432      | no   | no                         |
| LiveKit         | langtutor-livekit         | 7880 (TCP), 7881-2 UDP | no | **yes**                 |
| STT (speaches)  | langtutor-stt             | 127.0.0.1:8010      | yes  | no                         |
| TTS (fish)      | langtutor-tts             | 127.0.0.1:8011      | yes  | no                         |
| Avatar          | langtutor-avatar          | 127.0.0.1:8012      | yes  | no                         |

---

## 1. Prerequisites (what the operator provides)

Fill these into the template below and keep a copy — we'll reference them
throughout. Treat `[brackets]` as placeholders to replace.

| Name                        | Example                                        | Where used                       |
|-----------------------------|------------------------------------------------|----------------------------------|
| `DOMAIN`                    | `langtutor.app`                                | Caddy, CORS                      |
| `API_HOST`                  | `api.langtutor.app`                            | Mobile app, Caddy                |
| `ADMIN_HOST`                | `admin.langtutor.app`                          | Admin console, Caddy             |
| `LIVEKIT_HOST`              | `livekit.langtutor.app`                        | LiveKit WSS                      |
| `ADMIN_EMAIL`               | `ops@langtutor.app`                            | Let's Encrypt                    |
| `DB_PASSWORD`               | generate: `openssl rand -base64 32`            | Postgres                         |
| `JWT_SECRET`                | generate: `openssl rand -hex 64`               | Backend JWT                      |
| `LIVEKIT_API_KEY`           | generate: `openssl rand -hex 16`               | LiveKit + backend                |
| `LIVEKIT_API_SECRET`        | generate: `openssl rand -hex 32`               | LiveKit + backend                |
| `GEMINI_API_KEY`            | `AIzaSy...` (from aistudio.google.com)         | Tutor/coordinator agents         |
| `GOOGLE_CLIENT_ID_WEB`      | `...apps.googleusercontent.com`                | Backend verifies ID tokens       |
| `APPLE_CLIENT_ID`           | `app.langtutor.mobile`                         | Apple sign-in                    |

DNS A records: point `api.<domain>`, `admin.<domain>`, and
`livekit.<domain>` at the server's public IP **before** starting the Caddy
phase (Let's Encrypt DNS-01 or HTTP-01 won't succeed otherwise).

---

## 2. Phase 1 — Server provisioning

### 2.1 Create a deploy user

Run as `root` (or via `sudo`) — only needed once per box.

```bash
adduser --disabled-password --gecos "" langtutor
usermod -aG sudo langtutor
install -d -o langtutor -g langtutor -m 700 /home/langtutor/.ssh
# Copy operator's SSH key here:
echo "ssh-ed25519 AAAA... operator@laptop" > /home/langtutor/.ssh/authorized_keys
chown langtutor:langtutor /home/langtutor/.ssh/authorized_keys
chmod 600 /home/langtutor/.ssh/authorized_keys

# Harden sshd
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload sshd
```

**Verify:** from your workstation `ssh langtutor@<server-ip>` should succeed;
`ssh root@<server-ip>` should fail.

### 2.2 System update + firewall

As `langtutor` user, `sudo -i` for the rest of Phase 1–2.

```bash
apt-get update && apt-get -y dist-upgrade

# UFW firewall — default deny inbound, allow what we need
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp              # SSH
ufw allow 80/tcp              # HTTP (redirects to HTTPS)
ufw allow 443/tcp             # HTTPS
ufw allow 7880/tcp            # LiveKit signalling (WebSocket)
ufw allow 7881/tcp            # LiveKit TCP fallback
ufw allow 7881/udp            # LiveKit WebRTC
ufw allow 7882/udp            # LiveKit WebRTC
ufw allow 50000:60000/udp     # LiveKit media ports range
ufw --force enable
```

**Verify:** `ufw status` shows all the rules above as ALLOW.

### 2.3 Install Docker Engine + Compose plugin

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# Add deploy user to docker group
usermod -aG docker langtutor

# Log out and back in (or: newgrp docker) for group change to apply
```

**Verify:** `docker run --rm hello-world` prints the hello banner.

### 2.4 Install NVIDIA driver + Container Toolkit

```bash
# Pick the recommended driver version for the 3090
ubuntu-drivers autoinstall
reboot
```

After reboot:

```bash
# NVIDIA Container Toolkit (for GPU access from Docker)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb #deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] #g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update
apt-get install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
```

**Verify:**
```bash
nvidia-smi                    # should list the 3090 at 24 GB
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```
Both commands must show the GPU. If the second fails, the toolkit is not
registered — redo `nvidia-ctk runtime configure`.

### 2.5 Install Caddy (for TLS termination)

```bash
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
  | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy
```

**Verify:** `systemctl status caddy` shows `active (running)`. Visiting
`http://<server-ip>` returns the default Caddy page.

---

## 3. Phase 2 — Clone + configure

Run the rest as the `langtutor` user, not root.

### 3.1 Clone the repo

```bash
cd ~
git clone https://github.com/vatzcar/langtutor2.git langtutor
cd langtutor
```

### 3.2 Create production env files

**`~/langtutor/backend/.env`** — backend configuration. The `SECRETS` block
comes from the table in §1.

```ini
# --- Database ---
LANGTUTOR_DATABASE_URL=postgresql+asyncpg://postgres:[DB_PASSWORD]@db:5432/langtutor

# --- Auth ---
LANGTUTOR_SECRET_KEY=[JWT_SECRET]
LANGTUTOR_ALGORITHM=HS256
LANGTUTOR_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# --- Social login ---
LANGTUTOR_GOOGLE_CLIENT_ID=[GOOGLE_CLIENT_ID_WEB]
LANGTUTOR_APPLE_CLIENT_ID=[APPLE_CLIENT_ID]

# --- LiveKit ---
LANGTUTOR_LIVEKIT_URL=wss://[LIVEKIT_HOST]
LANGTUTOR_LIVEKIT_API_KEY=[LIVEKIT_API_KEY]
LANGTUTOR_LIVEKIT_API_SECRET=[LIVEKIT_API_SECRET]

# --- Gemini ---
LANGTUTOR_GEMINI_API_KEY=[GEMINI_API_KEY]

# --- AI service base URLs (all on the same host, localhost-bound) ---
LANGTUTOR_STT_BASE_URL=http://stt:8000
LANGTUTOR_TTS_BASE_URL=http://tts:8080
LANGTUTOR_AVATAR_BASE_URL=http://avatar:8000
LANGTUTOR_AVATAR_ENABLED=false
LANGTUTOR_STT_MODEL=Systran/faster-whisper-base.en

# --- Uploads ---
LANGTUTOR_UPLOAD_DIR=/app/uploads
LANGTUTOR_MAX_UPLOAD_SIZE_MB=10
```

**`~/langtutor/livekit.yaml`** — LiveKit config (read by the livekit
container via a mount we'll add in the compose override). Replace the
`[LIVEKIT_*]` values.

```yaml
port: 7880
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
keys:
  [LIVEKIT_API_KEY]: [LIVEKIT_API_SECRET]
```

**`~/langtutor/.env.prod`** — for docker-compose variable substitution.

```ini
DB_PASSWORD=[DB_PASSWORD]
LIVEKIT_CONFIG=./livekit.yaml
DOMAIN=[DOMAIN]
API_HOST=[API_HOST]
ADMIN_HOST=[ADMIN_HOST]
LIVEKIT_HOST=[LIVEKIT_HOST]
```

**Verify:** `chmod 600 .env.prod backend/.env livekit.yaml` — these contain
secrets.

### 3.3 Create `docker-compose.prod.yml` (production overrides)

This overrides the dev `docker-compose.yml` with:
- Localhost-only port binds (only Caddy/LiveKit face the internet)
- Postgres password from env
- LiveKit config mount
- Restart policies

```yaml
# ~/langtutor/docker-compose.prod.yml
services:
  db:
    image: postgres:16-alpine
    container_name: langtutor-db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: langtutor
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 15s
      retries: 5

  backend:
    build: ./backend
    container_name: langtutor-backend
    restart: always
    env_file: ./backend/.env
    ports:
      - "127.0.0.1:8001:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend/uploads:/app/uploads
    command:
      ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
       "--workers", "2"]

  livekit:
    image: livekit/livekit-server:latest
    container_name: langtutor-livekit
    restart: always
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7881:7881/udp"
      - "7882:7882/udp"
      - "50000-60000:50000-60000/udp"
    volumes:
      - ${LIVEKIT_CONFIG}:/etc/livekit.yaml:ro
    command: ["--config", "/etc/livekit.yaml"]

volumes:
  pgdata:
```

---

## 4. Phase 3 — Bring up the core stack

```bash
cd ~/langtutor
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d db livekit backend
```

First boot pulls images and builds the backend container (~3 min).

### 4.1 Seed the database (first deploy only)

```bash
docker compose exec backend python scripts/seed.py
```

Expected output: `Seed data created successfully! Admin: admin@langtutor.app / admin123`.

**Then immediately change the admin password:**

```bash
docker compose exec db psql -U postgres -d langtutor \
  -c "DELETE FROM admin_users WHERE email='admin@langtutor.app';"
# Create a new admin via the admin console once Caddy is up, OR:
docker compose exec backend python -c "
import asyncio
from app.database import async_session_factory
from app.models.admin import AdminUser, AdminRole
from app.utils.security import hash_password
from sqlalchemy import select

async def _go():
    async with async_session_factory() as db:
        r = (await db.execute(select(AdminRole).where(AdminRole.name=='Super Admin'))).scalar_one()
        db.add(AdminUser(email='you@yourdomain.com', name='You',
                         password_hash=hash_password('a-strong-password'),
                         role_id=r.id, is_active=True))
        await db.commit()
asyncio.run(_go())
"
```

**Verify:**
```bash
curl http://127.0.0.1:8001/health                 # {"status":"ok"}
docker compose ps                                  # all 3 containers healthy
docker logs langtutor-livekit --tail 20            # no ERROR lines
```

---

## 5. Phase 4 — Bring up the AI stack

```bash
cd ~/langtutor
docker compose -f docker-compose.ai.yml up -d stt
# Don't start tts/avatar yet if you want to stage cautiously.
```

### 5.1 Smoke-test STT

Wait ~60 seconds for the model to download into the `ai-models` volume.

```bash
curl -fsSL https://www.w3.org/2010/05/sound/sample.wav -o /tmp/sample.wav
curl -F file=@/tmp/sample.wav \
     -F "model=Systran/faster-whisper-base.en" \
     http://127.0.0.1:8010/v1/audio/transcriptions
```

Should return JSON with a `text` field. If 503 or timeout, wait longer —
first call compiles/loads the model.

### 5.2 Start TTS

```bash
docker compose -f docker-compose.ai.yml up -d --build tts
```

First build takes 15-30 min (fish-speech clones from source, installs
torch + rust + native deps). Follow progress:

```bash
docker compose -f docker-compose.ai.yml logs -f tts
```

Once up, first transcription call will download ~2 GB of Fish-Speech
weights — again, wait and watch logs.

**Smoke-test:**

```bash
curl -X POST -H 'Content-Type: application/json' \
     -d '{"text":"Hello from production."}' \
     http://127.0.0.1:8011/v1/tts -o /tmp/out.wav
file /tmp/out.wav                    # should report: RIFF (little-endian)...
```

### 5.3 Avatar (optional — only if you want real-time avatar video)

Avatar is disabled by default (`LANGTUTOR_AVATAR_ENABLED=false`).
**Do not enable on the 3090 until STT+TTS are stable** — avatar eats
another ~3.5 GB of VRAM and has known upstream API drift that may need
manual patching (see `services/ai/avatar/README.md`).

When you're ready:

```bash
docker compose -f docker-compose.ai.yml up -d --build avatar
# After successful smoke test, flip the backend flag:
sed -i 's/LANGTUTOR_AVATAR_ENABLED=false/LANGTUTOR_AVATAR_ENABLED=true/' backend/.env
docker compose -f docker-compose.prod.yml restart backend
```

---

## 6. Phase 5 — Build and deploy the admin console

### 6.1 Build on the server (needs Node)

```bash
# Install Node LTS via nvm to avoid apt's stale version
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20

cd ~/langtutor/admin
npm ci

# Point the admin build at the production API URL
cat > .env.production <<EOF
VITE_API_BASE_URL=https://[API_HOST]/api/v1
EOF

# Patch src/api/client.ts if it uses a hardcoded baseURL (current code does);
# change `const API_BASE_URL = 'http://localhost:8001/api/v1'` to
# `const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1'`
# This is a one-time code change; commit it.

npm run build                  # emits ./dist
```

**Verify:** `ls dist/index.html` exists and `dist/assets/` has the JS
bundles.

### 6.2 Expose the build to Caddy

```bash
sudo install -d -o caddy -g caddy /var/www/langtutor-admin
sudo rsync -a --delete ~/langtutor/admin/dist/ /var/www/langtutor-admin/
```

---

## 7. Phase 6 — Caddy reverse proxy + TLS

### 7.1 Write the Caddyfile

`/etc/caddy/Caddyfile`:

```caddyfile
{
    email [ADMIN_EMAIL]
}

# --- Admin console (SPA) ---
[ADMIN_HOST] {
    root * /var/www/langtutor-admin
    encode gzip zstd
    try_files {path} /index.html
    file_server
    header {
        Strict-Transport-Security "max-age=31536000"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}

# --- Backend API ---
[API_HOST] {
    encode gzip zstd
    reverse_proxy 127.0.0.1:8001 {
        header_up Host {host}
        header_up X-Forwarded-Proto {scheme}
    }
    @large path /api/v1/admin/languages/*/icon /api/v1/admin/personas/*/image
    request_body @large {
        max_size 20MB
    }
    # Serve uploads directly for efficiency
    handle /uploads/* {
        root * /home/langtutor/langtutor/backend
        file_server
    }
    header {
        Strict-Transport-Security "max-age=31536000"
    }
}

# --- LiveKit signalling (WebSocket) ---
[LIVEKIT_HOST] {
    reverse_proxy 127.0.0.1:7880 {
        header_up Host {host}
    }
}
```

Replace the `[bracketed]` placeholders with real values.

### 7.2 Validate and reload

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo journalctl -u caddy -n 50 --no-pager
```

Caddy will request Let's Encrypt certs automatically on first request —
expect ~30 seconds of "obtaining certificate" log lines. If it fails:
- DNS isn't pointing at the server yet → fix DNS, wait 5 min, reload
- Port 80 blocked → recheck UFW
- Rate limited by Let's Encrypt → wait and retry

**Verify:**
```bash
curl -I https://[API_HOST]/health           # HTTP/2 200
curl -I https://[ADMIN_HOST]/               # HTTP/2 200
curl -I https://[LIVEKIT_HOST]              # HTTP/2 200 or 400 (WS only)
```

Visit `https://[ADMIN_HOST]` in a browser — admin console loads, login
form appears. Sign in with the admin you created in §4.1.

---

## 8. Phase 7 — Mobile app configuration

On the workstation (not the server), update the Flutter config to point
at production and rebuild the APK/IPA.

`mobile/lib/config/constants.dart`:

```dart
static const String apiBaseUrl = 'https://[API_HOST]/api/v1';
static const String liveKitUrl = 'wss://[LIVEKIT_HOST]';
```

Then:
```bash
cd mobile
flutter clean
flutter build apk --release                 # or appbundle
# For iOS: flutter build ipa --release
```

**Google OAuth:**
- Keep the Android OAuth client (package `com.example.langtutor` + debug
  SHA-1 for dev).
- Add a **second** Android OAuth client with the **release** keystore
  SHA-1 for signed builds.
- Add both SHA-1s to the same client if you prefer a single OAuth app.

---

## 9. Phase 8 — Systemd watchdogs (auto-restart on reboot)

Docker's `restart: always` handles container-level crashes, but we also
want the stacks to come up on host reboot.

`/etc/systemd/system/langtutor-core.service`:

```ini
[Unit]
Description=LangTutor core stack (db, backend, livekit)
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=true
User=langtutor
WorkingDirectory=/home/langtutor/langtutor
ExecStart=/usr/bin/docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/langtutor-ai.service`:

```ini
[Unit]
Description=LangTutor AI stack (stt, tts, avatar)
Requires=docker.service langtutor-core.service
After=langtutor-core.service

[Service]
Type=oneshot
RemainAfterExit=true
User=langtutor
WorkingDirectory=/home/langtutor/langtutor
ExecStart=/usr/bin/docker compose -f docker-compose.ai.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.ai.yml down

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now langtutor-core langtutor-ai
sudo systemctl status langtutor-core langtutor-ai
```

---

## 10. Phase 9 — Backups

### 10.1 Postgres nightly dump

`/home/langtutor/backup-db.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%F-%H%M)
OUT_DIR=/home/langtutor/backups
mkdir -p "$OUT_DIR"
docker exec langtutor-db pg_dump -U postgres -d langtutor -F c \
  > "$OUT_DIR/langtutor-$TS.dump"
# Keep 14 daily + 8 weekly
find "$OUT_DIR" -name "langtutor-*.dump" -mtime +14 -delete
```

```bash
chmod +x /home/langtutor/backup-db.sh
# Daily at 03:00 server time
(crontab -l 2>/dev/null; echo "0 3 * * * /home/langtutor/backup-db.sh") | crontab -
```

### 10.2 Uploads directory

Uploads live in `~/langtutor/backend/uploads/`. Sync them to object
storage if you have it:

```bash
# Example: rclone to Backblaze B2 — configure with `rclone config` once
rclone sync ~/langtutor/backend/uploads b2:langtutor-backup/uploads --progress
```

Add to crontab after the db dump.

### 10.3 Restore drill (do this ONCE after setup)

```bash
# Drop + recreate DB, restore from dump
docker exec langtutor-db dropdb -U postgres langtutor
docker exec langtutor-db createdb -U postgres langtutor
docker exec -i langtutor-db pg_restore -U postgres -d langtutor \
  < /home/langtutor/backups/langtutor-YYYY-MM-DD-HHMM.dump
```

If the restore completes without errors and the admin console still logs
in, you've validated the backup path.

---

## 11. Phase 10 — End-to-end smoke test

From an external network (not the server itself):

1. **API health**:
   `curl https://[API_HOST]/health` → `{"status":"ok"}`
2. **Admin login**: visit `https://[ADMIN_HOST]`, sign in, click
   through each sidebar item — all pages load, no 500 errors in the
   backend logs (`docker logs langtutor-backend --tail 50`).
3. **Mobile Google sign-in**: install the release APK, sign in → lands
   on home screen.
4. **Audio loop** (once TTS is up): start a voice session; confirm the
   tutor greets you (TTS fires) and your reply is transcribed (STT fires).
   Check `docker logs langtutor-stt` and `docker logs langtutor-tts` for
   live request activity.
5. **LiveKit WebRTC**: monitor `docker logs langtutor-livekit` while a
   call is active — should see "participant joined" lines.
6. **VRAM headroom**: `nvidia-smi` during an active session. Expect
   ~7-10 GB used with STT+TTS loaded. If >20 GB, investigate before
   accepting more concurrent users.

---

## 12. Day-2 operations

### 12.1 Deploy an update

```bash
cd ~/langtutor
git fetch
git log HEAD..origin/main --oneline      # review what's coming
git pull

# Rebuild only what changed
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend

# If admin changed:
cd admin && npm ci && npm run build
sudo rsync -a --delete dist/ /var/www/langtutor-admin/

# If AI stack changed:
docker compose -f docker-compose.ai.yml build tts avatar
docker compose -f docker-compose.ai.yml up -d
```

### 12.2 Rollback

```bash
cd ~/langtutor
git log --oneline -10        # find the previous good commit
git checkout <sha>
docker compose -f docker-compose.prod.yml up -d --build backend
```

If a migration broke the DB, restore from the most recent `pg_dump` in
`~/backups/` (§10.3). **Always take a dump right before rolling out a
migration.**

### 12.3 Log aggregation (quick)

```bash
# Real-time
docker compose -f docker-compose.prod.yml logs -f --tail 100 backend
docker compose -f docker-compose.ai.yml logs -f --tail 100

# Historical — docker rotates logs by default; configure larger retention in
# /etc/docker/daemon.json:
#   { "log-driver": "json-file", "log-opts": { "max-size": "100m", "max-file": "5" } }
```

### 12.4 Common failure modes

| Symptom                                   | Likely cause                                   | Fix                                                         |
|-------------------------------------------|------------------------------------------------|-------------------------------------------------------------|
| Caddy 502 on /api/*                       | Backend crashed or unhealthy                   | `docker ps`, check backend logs                             |
| Backend 500 on /auth/social-login         | DB unreachable or Gemini key missing           | Check `.env`, `docker exec backend env \| grep GOOGLE`      |
| Mobile: connection refused                | Backend not on public interface                | Confirm Caddy proxying, not raw 8001                        |
| LiveKit "ICE candidate gathering failed"  | UDP ports blocked                              | `ufw status`, confirm 7881-7882 + 50000-60000 are open      |
| `nvidia-smi` works but Docker GPU fails   | Container toolkit misconfigured after upgrade  | `sudo nvidia-ctk runtime configure --runtime=docker && systemctl restart docker` |
| OOM during avatar render                  | Concurrent session count too high              | Lower max concurrent; consider second GPU                   |
| Fish-Speech slow first call               | Torch compile warmup                           | Wait; second call should be fast                            |
| Let's Encrypt cert renew fails            | Port 80 blocked or DNS changed                 | `ufw allow 80/tcp`, `sudo systemctl reload caddy`           |

### 12.5 Scaling signals

Signs it's time to add a second GPU box or horizontally scale:

- `nvidia-smi` at >90% VRAM for >30% of the day
- Backend requests queueing (gunicorn worker saturation in logs)
- STT/TTS first-token latency p95 > 1.5s
- LiveKit dropping "ICE failed" > 5% of sessions

When you do scale: put the AI stack on its own machine(s), with the
backend calling it over TLS internal. The backend and DB can stay on a
CPU-only box since they're not GPU-bound.

---

## 13. Security checklist (review quarterly)

- [ ] SSH is key-only, root login disabled
- [ ] UFW allows exactly the ports in §2.2
- [ ] All secrets are 600 permission, owned by `langtutor`
- [ ] Postgres only listens on 127.0.0.1, never public
- [ ] `LANGTUTOR_SECRET_KEY` has 64+ chars of entropy
- [ ] Gemini and Google OAuth keys rotated yearly
- [ ] Admin password uses a password manager, 20+ chars
- [ ] Backups include a successful restore drill in the last 30 days
- [ ] System packages updated: `apt list --upgradable` shows nothing
- [ ] Docker base images rebuilt monthly: `docker compose build --pull`

---

## 14. What to hand off to the next operator

1. This file (always committed to the repo).
2. The filled-in table from §1 stored in a password manager (Bitwarden,
   1Password, Infisical — NOT in git).
3. SSH private key for the `langtutor` deploy user.
4. The latest successful pg_dump filename from `~/backups/`.
5. A 5-minute recording of `docker compose ps` and `nvidia-smi` from a
   healthy state so comparisons are possible during an incident.

---

**Last updated:** aligns with the state of the repo at the commit that
introduced this file. When you materially change the architecture (e.g.
split GPU to a separate host, move Postgres to managed service), update
this document **in the same commit** as the change.
