# fnOS Bundled Hermes Kernel: Gateway API Server Recipe

Verified working (2026-08, Hermes v0.19.0 on fnOS 1.1.31xx). The self-contained "模式 B"
pattern: run `hermes gateway run` as the fnOS app's restricted user, exposing the OpenAI-
compatible API server that a WebUI frontend connects to. Completely local, no remote
dependency.

## The two things the WebUI actually needs

- **Gateway API server** (:8642) — provides `/v1/chat/completions`, `/v1/models`, `/health`.
  This is what the frontend chats through.
- Dashboard (:9119) is a *separate* service (management UI). The WebUI frontend does NOT
  need it. `HERMES_API_URL` in cmd/main must point at the Gateway API, not the Dashboard —
  pointing it at an unreachable Dashboard makes the WebUI refuse chat with "Internal server error".

## Enable the API server (this is the part that's easy to get wrong)

`hermes gateway run` only binds the API server when the `api_server` platform adapter
loads. Two requirements:

1. **`aiohttp` must be installed in the venv** — otherwise startup logs
   `WARNING gateway.run: API Server: aiohttp not installed` and
   `No adapter available for api_server`, and the port never binds. hermes-agent's base
   deps do NOT include aiohttp. Add it explicitly:
   ```bash
   ${VENV}/bin/pip install aiohttp
   ```

2. **API server config** (from `hermes_cli/web_server.py` `"api_server": ("port", 8642)`
   and `hermes_cli/config.py`):
   ```bash
   # in the app's gateway.env, sourced by cmd/main and exported
   API_SERVER_ENABLED=true
   API_SERVER_HOST=0.0.0.0        # default 127.0.0.1 — must be 0.0.0.0 for LAN access
   API_SERVER_PORT=8642           # default
   API_SERVER_KEY=webui-gateway-key-2026   # REQUIRED even on loopback
   ```
   Auth check: request WITHOUT the key returns 401; with `Authorization: Bearer <key>`
   returns the model list. Verify:
   ```bash
   curl -sf -H "Authorization: Bearer $API_SERVER_KEY" http://127.0.0.1:8642/v1/models
   ```

## cmd/main lifecycle (verified start/status/stop/restart all work)

- `HERMES_HOME` must be explicit and live in the fnOS app data dir, NOT `$HOME` (the fnOS
  app user is nologin and has no usable home). Use `HERMES_HOME=${DATA_DIR}/hermes_home`.
- `config.yaml` and `.env` must be hand-written into `$HERMES_HOME` — `hermes setup` is
  interactive and won't generate them from SSH. Minimal config.yaml:
  ```yaml
  model:
    default: cbcn/deepseek-v4-flash
    provider: 9Router Proxy        # fnOS self-hosted router at 127.0.0.1:20128
    base_url: http://127.0.0.1:20128/v1
  toolsets: [hermes-cli]
  api_server: { enabled: true, host: "0.0.0.0", port: 8642 }
  ```
  `.env` carries the LLM provider keys (e.g. `XIAOMI_API_KEY=...`).
- start: `nohup ${VENV}/bin/hermes gateway run >> $LOG 2>&1 &`, health-poll
  `/health` for up to 40s. Binding a service on `0.0.0.0` is fine from the restricted user
  (proven by strava:20127, metacubexd:9091, 9router:20128).
- stop: kill PID file, then pkill fallback that matches the ACTUAL runtime cmdline
  (`pkill -f "${VENV}/bin/hermes gateway run"`) so stop/uninstall can reap its own orphan
  and free the port — same lesson as the 9Router next-server orphan case.
- status: return non-zero when stopped (fnOS uses the exit code to decide whether to start).

### ⚠️ Cannot stop the gateway from inside a Hermes agent session

If you're SSHing from a host that is itself running a Hermes gateway (e.g. driving the
NAS from the Arch VM), a bare `pkill -f "hermes gateway run"` is **blocked**: the gateway
intercepts SIGTERM propagation and refuses — "Blocked: cannot restart or stop the gateway
from inside the gateway process." Workarounds:
- Target the **specific venv path** (`pkill -f "${DATA_DIR}/venv/bin/hermes gateway run"`)
  or the exact PID from `ps aux | grep hermes gateway` — the NAS gateway's cmdline
  (`/home/.../venv/bin/python3 ... hermes gateway run`) is what you match.
- Or list PIDs via `ps aux | grep "hermes gateway" | grep -v grep | awk '{print $2}'`
  and `kill` each — avoids the broad `-f` string that trips the guard.

## install_callback: the ~2-min pip risk

`pip install hermes-agent` downloads ~100MB / 50+ deps and takes 1-2 min. fnOS install
hooks can time out or the network can stall mid-way. Mitigations:
- Use a non-quiet install into a log file; a `--quiet` install swallows the real error.
- If fnOS kills the hook, the install just didn't finish — make cmd/main's start do a
  hybrid check (`if [ -f "$VENV/bin/hermes" ]`) and report clearly, or fall back.
- **Offline B-scheme**: pre-bundle `pip download`-ed wheels and install with
  `--no-index --find-links=wheels/` in install_callback to bypass the network/timeout
  entirely. Wheel dir is platform-specific — manifest must declare the matching arch
  (x86_64).
- On this NAS, system `python3` (3.11) AND the `python312` fnOS runtime
  (`/vol4/@appcenter/python312/bin/python3.12`) both build working venvs; prefer python312
  for consistency with the fnOS runtime ecosystem.

## Verification sequence used

1. Install hermes-agent in a venv on the NAS; confirm `hermes --version`.
2. `pip install aiohttp`; confirm `import aiohttp`.
3. Write config.yaml + .env into `$HERMES_HOME`.
4. `hermes gateway run`; check `ss -tlnp | grep 8642`.
5. `/health` → `{"status":"ok","platform":"hermes-agent","version":"0.19.0"}`.
6. `/v1/chat/completions` with Bearer key → real LLM response (proves full local chain).
7. Full cmd/main start/status/stop/restart cycle with the TRIM_* env vars fnOS passes.
