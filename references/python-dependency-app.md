# Packaging Python-Heavy Dependencies (hermes-agent case)

How to wrap a large Python pip dependency (50+ deps, ~100MB+, e.g. `hermes-agent`)
into an fnOS app that runs a long-lived background service (a Gateway/API server).
Verified 2026-08 building `hermes-core-fnos` (local Hermes kernel + Gateway API).

## Architecture: fnOS app = venv in DATA_DIR + lifecycle scripts

fnOS apps run as a **dedicated `nologin` user** (e.g. `HermesCore`, uid ~975), confirmed
via a diagnostic log in `cmd/main` (write unconditional `USER=$(id -un) UID=$(id -u)`,
`TRIM_APPDEST`, `TRIM_PKGVAR`). Key facts:
- App user CAN `python3 -m venv` + `pip install` into `/vol4/@appdata/<App>/`
- App user CAN bind a TCP port and run a long-lived service (strava:20127, 9router:20128)
- App user CANNOT be logged into interactively (`/usr/sbin/nologin`), but CAN run processes
- **Never rely on `$HOME`** — app user may have no home dir. Set `HERMES_HOME=/vol4/@appdata/<App>/hermes_home` explicitly.

## install_callback: two modes

```bash
# A) online: venv + pip install (fpk small ~150KB, needs network, 1-2 min)
PY=/usr/bin/python3
[ -x /vol4/@appcenter/python312/bin/python3.12 ] && PY=/vol4/@appcenter/python312/bin/python3.12
"$PY" -m venv "$VENV"
"$VENV/bin/pip" install --quiet hermes-agent aiohttp pyyaml cryptography
# on failure retry via proxy: --proxy http://127.0.0.1:7890

# B) offline: extract a prebuilt venv tarball bundled in the fpk (fpk ~150MB, instant, no network)
if [ -f "$APP_DIR/venv.tar.gz" ]; then
  tar xzf "$APP_DIR/venv.tar.gz" -C "$DATA_DIR"
fi
```

**Pitfalls:**
- **`aiohttp` is REQUIRED** for the `api_server` Gateway platform. Without it: `WARNING gateway.run: API Server: aiohttp not installed` → port never binds. `pip install hermes-agent` does NOT pull aiohttp transitively in this case.
- `pip install hermes-agent` takes 1–2 min (50+ deps). SSH foreground with a 60s timeout will kill it mid-download. Run backgrounded, or use the offline tarball.
- `--quiet` swallows real errors — when debugging, run `pip install` WITHOUT `--quiet` to see the actual failure.
- The bundled offline venv is architecture-specific (x86_64). Keep `arch = x86_64` in manifest.
- `__pycache__` dirs get created inside the package tree when you `python3 -m py_compile` — **strip `find . -name __pycache__ -exec rm -rf {} +` before `fnpack build`** and add `__pycache__/` + `*.pyc` to `.gitignore`, or the fpk ships stale .pyc files.

## Gateway API server config (hermes-agent)

The WebUI/chat backend connects to the kernel's OpenAI-compatible API (`/v1/chat/completions`,
`/v1/models`, `/health`). Configure via env vars that the running process must see:
```bash
export HERMES_HOME=/vol4/@appdata/<App>/hermes_home
export API_SERVER_ENABLED=true
export API_SERVER_HOST=0.0.0.0     # default 127.0.0.1 — must be 0.0.0.0 for LAN reach
export API_SERVER_PORT=8642
export API_SERVER_KEY=webui-gateway-key-2026   # required even on loopback
```
Then `nohup $VENV/bin/hermes gateway run >> log 2>&1 &`. Health poll `curl -sf -H "Authorization: Bearer $KEY" http://127.0.0.1:8642/health`.

**config.yaml must define full `custom_providers`** (name + base_url + api_key + models), not just `model.default`. Otherwise chat fails with `Unknown provider 'xxx'`.

## LLM provider dual-channel (generic fallback)

Users may use a specific local proxy (9Router) OR any direct OpenAI-compatible API. Support both in the wizard:
- `router_api_key` — local 9Router (`http://127.0.0.1:20128/v1`)
- `llm_base_url` + `llm_api_key` + `llm_model` — generic fallback (any OpenAI-compatible endpoint)
- Priority: if `llm_base_url` set use "Custom LLM" provider, else 9Router.
- A proxy's `/v1/models` may be key-free but `/v1/chat/completions` requires the key → always make the key a user-configurable wizard field. The DB may store keys masked (`<YOUR_API_KEY>`), unrecoverable — so user must supply it.

## Wizard field name → lifecycle var mapping (recurring pitfall)

- `wizard/install` fields are passed as `wizard_<field>` to **install_callback**.
- `wizard/config` (App Settings page) fields are passed as **bare names** to **config_callback**.
- `install_callback` must persist the `wizard_*` values to a config file (`gateway.env`) that `cmd/main` sources at runtime — wizard values do NOT reach cmd/main directly.
- `config_callback` persists bare names to the same file.

## Locating sibling files next to a lifecycle script (`BASH_SOURCE[0]`)

In fnOS 1.1.31xx, `TRIM_APPDEST=/vol4/@appcenter/<App>` but the executed `cmd/main` lives at
`/var/apps/<App>/cmd/main`. So `${APP_DIR}/cmd/<sibling>` may NOT exist even though the file is
right next to the running script. Resolve from the script's own path (reliable in all fnOS versions):
```bash
CMD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIBLING_SRC="${CMD_DIR}/sibling.py"
# fall back to candidate dirs, incl. DATA_DIR (workaround for an already-installed app)
[ -f "${APP_DIR}/cmd/sibling.py" ] && SIBLING_SRC="${APP_DIR}/cmd/sibling.py"
[ -f "${DATA_DIR}/sibling.py" ] && SIBLING_SRC="${DATA_DIR}/sibling.py"
```
Symptom when wrong: `sibling.py not found (/vol4/@appcenter/<App>/cmd/sibling.py)` though the file
exists in `/var/apps/<App>/cmd/`. Hot-workaround for an already-installed app: copy the file into
`$DATA_DIR` (app user-writable) so the `DATA_DIR` fallback finds it — no reinstall needed.

## Mobile App iframe white-screen (`WebKitErrorDomain code=102`)

Phone fnOS App opens desktop icons via a **WebView iframe**. If the app entry (`app/ui/config`
`type:"url"`) points at a JSON API endpoint (e.g. `/health`) with no CORS headers, the iframe
fails to load → white screen, "无法访问此页面 frame load interrupted", `WebKitErrorDomain code=102`.
**Fix:** the entry must point at a real HTML page. For a pure-backend app, ship a tiny status page
(stdlib `http.server` serving an HTML snippet that probes the backend health and renders 运行中/healthy/version).
Point `app/ui/config` at that page's port. Start it in `cmd/main start`, stop it in `stop`.

## Debugging two apps that both white-screen (systematic)

When a user reports "both apps white-screen", DON'T assume one cause. Check each independently:
1. Is the backend port listening? `ss -tlnp | grep <port>` (may differ per app — one up, one down).
2. Which user owns the process? If the SSH user (`<user>`) owns it, App Center (app user) may be failing to start it.
3. Check fnOS lifecycle log `/var/log/apps/<App>.log` (repeated `stopped` = App Center never started it)
   vs the app's own log in `$DATA_DIR`.
4. **Ownership pollution:** manually starting an app via SSH as `<user>` makes the venv/data dirs
   `<user>`-owned. App Center (app user) then CANNOT use them → app stays `stopped`, port never binds.
   Fix: `chown -R <AppUser>:<AppUser> /vol4/@appdata/<App>/{venv,hermes_home,state}`.
5. **Cross-user kill:** SSH `<user>` may get `kill: (PID) - Operation not permitted` on an app-user
   process (app owns its process; only App Center or root can reap it). A stale app-user process holding
   a port can't be killed from SSH — App Center must do stop/restart, or root must kill.
6. A `start()` that short-circuits `port already serving → return 0` will skip starting any companion
   service (e.g. a status page). Ensure `start()` doesn't return early before launching secondary services.
