# Hermes Agent Kernel as an fnOS App (模式 B 本地内核)

Verified 2026-08-03 — building a standalone Hermes Agent kernel fnOS app
(`hermes-core-fnos`) that runs a local Gateway API (port 8642), fully
self-contained on the NAS (no remote server dependency). Complement to
`hermes-webui-fnos` (the frontend).

## Architecture

```
fnOS
┌────────────────────────────────┐
│ Hermes Core  (:8642)           │
│   └─ hermes gateway run        │
│       └─ local venv hermes-agent│
│           └─ LLM (9Router / custom)│
└────────────────────────────────┘
```

- Kernel installed in `<DATA_DIR>/venv` (`/vol4/@appdata/<App>/venv`).
- `HERMES_HOME` MUST be set explicitly to `$DATA_DIR/hermes_home` — fnOS app
  users are nologin and may have no home dir. Never rely on `$HOME/.hermes`.
- `config.yaml` + `.env` written by `cmd/main` on first start (NOT `hermes setup`,
  which is interactive and fails non-interactively).

## Verified: restricted (nologin) users CAN run a Python kernel

Confirmed by reading a working app's `cmd/main` diagnostic log (`USER=strava
UID=969`, nologin shell) plus live testing:
- fnOS app center runs `cmd/main` as a dedicated nologin user (`TRIM_APPDEST`,
  `TRIM_PKGVAR` env vars are the correct paths; `PWD=/`).
- That user CAN `python3 -m venv`, `pip install` into `/vol4/@appdata/<App>/`,
  and bind TCP ports (strava:20127, metacubexd:9091, 9router:20128 all run this way).
- Use `/vol4/@appcenter/python312/bin/python3.12` if present (fnOS python312
  runtime), else `/usr/bin/python3`. System python3's venv+ensurepip work even
  when the `python3-venv` deb is not installed.

## Kernel startup env (api_server platform)

```bash
export HERMES_HOME=$DATA_DIR/hermes_home
export API_SERVER_ENABLED=true
export API_SERVER_HOST="${API_SERVER_HOST:-0.0.0.0}"   # default 127.0.0.1
export API_SERVER_PORT="${API_SERVER_PORT:-8642}"
export API_SERVER_KEY="${API_SERVER_KEY:-webui-gateway-key-2026}"  # required even on loopback
"$VENV/bin/hermes" gateway run &
```

- Port default 8642 (`"api_server": ("port", 8642)` in web_server.py).
- `API_SERVER_HOST` default is `127.0.0.1` — MUST set `0.0.0.0` for LAN/WebUI reach.
- **aiohttp is required** for the `api_server` adapter. `pip install hermes-agent`
  does NOT pull it automatically in this setup — without it you get
  `No adapter available for api_server` / port not bound. Install it explicitly:
  `pip install aiohttp pyyaml cryptography`.
- The Gateway API and the Dashboard (`hermes dashboard`, :9119) are SEPARATE
  services. WebUI only needs the Gateway API (`HERMES_API_URL` and
  `HERMES_WEBUI_GATEWAY_BASE_URL` should both point at the Gateway API, not :9119).

## LLM connection — dual-channel config

Users may use a local 9Router OR a raw OpenAI-compatible endpoint. Support both
via the install wizard / settings page:

- `router_api_key` — 9Router on the NAS (`http://127.0.0.1:20128/v1`), optional.
- Generic fallback: `llm_base_url` + `llm_api_key` + `llm_model` — any
  OpenAI-compatible API (direct, proxy, etc.).

`cmd/main` `write_config()` picks `model.default`:
- if `$LLM_BASE_URL` set → `provider: Custom LLM`, model from `$LLM_MODEL`
- else → `provider: 9Router Proxy`
- else → 9Router default

Both are emitted as `custom_providers` entries so either can be selected at runtime.

## install_callback — online vs offline (dual-mode)

`pip install hermes-agent` pulls 50+ deps (~100MB, 1-2 min) and may time out /
fail on constrained networks. Support BOTH:

```bash
OFFLINE_VENV="${APP_DIR}/venv.tar.gz"   # B: bundled, ~142MB
if [ -f "$OFFLINE_VENV" ]; then
    tar xzf "$OFFLINE_VENV" -C "$DATA_DIR"   # offline, instant
    [ -x "$VENV/bin/hermes" ] && exit 0
    rm -rf "$VENV"
fi
# else online: python3 -m venv + pip install hermes-agent (direct, then --proxy fallback)
```

Bundled venv must be built on the SAME arch (manifest `arch=x86_64`); the venv is
not portable across arches. Verified venv size ~142MB after clearing `__pycache__`/pip cache.

## fnOS lifecycle notes

- `cmd/main status()` MUST `return 1` when stopped (else App Center never calls start).
- `cmd/main stop` must pkill the ACTUAL runtime cmdline to reap orphaned kernels
  (`pkill -f "$VENV/bin/hermes gateway run"`), matching the 9Router orphan lesson.
- Manifest for a pure backend service: `service_port = 8642`, `ctl_stop = true`,
  `checkport = false` (avoid false port conflict when another instance lingers).
  `run-as: package` (config/privilege), data-share with 2 shares in config/resource.
- Entry: do NOT point `app/ui/config` at a JSON `/health` endpoint — that white-screens
  the mobile App (iframe + JSON + no CORS = `WebKitErrorDomain code=102`). Use a status
  page (see "Status page & web config").

### ⚠️ early-return 分支必须调 write_config()（2026-08-12 踩坑）

`cmd/main start()` 在检测到 gateway 已运行时会 early-return，**跳过 `write_config()`**。
结果 config.yaml 缺少 `dashboard.basic_auth` 段 → dashboard 启动时找不到 auth providers →
拒绝绑定 0.0.0.0 → "Chat unavailable: 1"。

**触发条件**：NAS 重启后 gateway 残留进程还在（端口 8642 可用），`start()` 进入
early-return 分支直接调 `start_dashboard()`。

**修复**：early-return 分支在 `start_dashboard()` 前先调 `write_config()`：
```bash
if [ -f "${PID_FILE}" ] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
    log "already running (pid $(cat "${PID_FILE}"))"
    # 重新生成 config.yaml (确保 dashboard.basic_auth 等段落存在)
    OLD_PLATFORMS=""
    [ -f "${HERMES_HOME}/config.yaml" ] && OLD_PLATFORMS="$(awk '/^platforms:/{flag=1} flag' "${HERMES_HOME}/config.yaml")"
    write_config
    start_status_server
    start_dashboard
    return 0
fi
```

### ⚠️ dashboard PTY 需要 node 在 PATH（2026-08-12 踩坑）

dashboard 启动 PTY 时 `shutil.which("node")` 找不到 node → `main.py exit 1` → "Chat unavailable: 1"。

**修复**：`setup_node_path()` 函数把 `hermes_home/node/bin` 加进 PATH：
```bash
setup_node_path() {
    local NODE_BIN="${HERMES_HOME}/node/bin"
    if [ -x "${NODE_BIN}/node" ]; then
        case ":${PATH}:" in
            *":${NODE_BIN}:"*) ;;
            *) export PATH="${NODE_BIN}:${PATH}" ;;
        esac
    fi
}
# 在 start_dashboard() 前调用
```

## Wizard field mapping (CRITICAL — two different prefixes)

- `wizard/install` (install wizard) → values passed to install lifecycle as
  **`wizard_<field>`** env vars. Persist them in `install_callback`:
  ```bash
  echo "ROUTER_API_KEY=\"${wizard_router_api_key:-}\"" > "$DATA_DIR/gateway.env"
  ```
- `wizard/config` (App Center settings page) → values passed to `config_callback`
  as **bare field names** (no `wizard_` prefix). Persist those too.
- `cmd/main` sources `gateway.env` at runtime to get the config.

## Status page & web config (v0.2.2+)

A pure-backend app still needs a desktop UI entry; give it a **status page service**
(`cmd/status_server.py`, pure Python stdlib — http.server + ThreadingHTTPServer,
zero deps, does NOT need venv). Listens on a separate port (8648).

```
GET /            → status HTML + config form (masked current values)
POST /api/config → save gateway.env (Bearer API key auth)
POST /api/restart → one-click kernel restart (Bearer auth)
```

- **Entry type decision**:
  - Complex SPA frontend (HermesWebUI) → `"type": "url"` (new tab). iframe
    cross-origin breaks it → blank screen.
  - Pure HTML status page (HermesCore) → `"type": "iframe"` (desktop window),
    renders fine in an iframe.
  - Match the entry `type` to whether the target page survives iframe embedding.
  - Do NOT point the entry at a JSON API endpoint (`/health`): mobile fnOS App
    loads entries via **WebView iframe**, JSON body + missing CORS → `WebKitErrorDomain
    code=102` ("frame load interrupted") → blank white screen. Point it at a real HTML page.
- **Status page path resolution (fnOS 1.1.31xx)**: `TRIM_APPDEST=/vol4/@appcenter/<App>`
  but the cmd scripts are at `/var/apps/<App>/cmd/`. Do NOT rely on `${APP_DIR}/cmd`
  to find `status_server.py`. Use the script's own dir:
  ```bash
  CMD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  STATUS_SRC="${CMD_DIR}/status_server.py"   # primary
  # fallbacks: ${APP_DIR}/cmd, ${APP_DIR}/target/cmd, ${DATA_DIR}
  ```
- Start it from `cmd/main` (pass `STATUS_PORT CORE_PORT CORE_API_KEY CORE_CONFIG CORE_CMD`);
  stop it in the same `stop()`. `SO_REUSEADDR`: `class Server(ThreadingHTTPServer): allow_reuse_address = True`.
- **Web config auth**: `POST /api/config` / `GET /api/config` require
  `Authorization: Bearer <API_SERVER_KEY>` → else 401. Mask secrets to first/last few chars.
- **Restart endpoint**: `subprocess.Popen(["bash", cmd_main, "restart"])` in background
  (don't block; don't let the status server kill itself).
- Write config to `${DATA_DIR}/gateway.env` (chmod 600), accept ONLY whitelisted fields.
- Three config surfaces coexist: install wizard / App Center settings page / web page.

## Cross-user orphan process (can't kill from SSH)

fnOS app processes run as a dedicated **app user** (e.g. `HermesCore` uid). SSH
user (<user>) gets `kill: Operation not permitted` trying to kill them. So:
- A lingering app-user kernel/status process holds the port; a manual
  `cmd/main restart` from SSH can't stop it → `start` sees the port busy and
  skips starting the status server.
- **Only App Center (running as the app user) or root can clear it.** Tell the user
  to App Center → stop → start. For local testing of a new version, use a DIFFERENT
  port (e.g. 8649) to avoid the occupied one.

## fpk build permission pitfall

`fnpack build` fails with `mkdir /tmp/fnpack.*/app/ui: permission denied` when
source dirs have wrong perms — a `cp`/`tar` that strips read/exec leaves `app/`
as `d---------` (owner-only, no read). **Fix: before `fnpack build`**:
```bash
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod 755 cmd/* wizard/*
```
Then build succeeds → `HermesCore.fpk`.

## Status page UI evolution (v0.3.7–v0.3.8)

The HermesCore status page went from single-page → top-tabs → **left sidebar nav**
(reference: 9Router). Reusable pattern for a fnOS web status page:

**Sidebar nav + mobile hamburger collapse**
```css
.layout { display:flex; }
.sidebar { width:200px; ... }           /* desktop fixed sidebar */
/* mobile */
@media (max-width:768px) {
  .sidebar { position:fixed; left:-200px; transition:left .2s; }
  .sidebar.open { left:0; }
  .sidebar-overlay.show { display:block; }   /* dim overlay */
  .hamburger { display:block; }
}
```
JS: `switchNav(name)` toggles `.nav-item.active` + shows `#panel-<name>`, and
collapses the sidebar on mobile (`if (innerWidth<=768) toggleSidebar(false)`).
`toggleSidebar()` toggles `.sidebar.open` + `.sidebar-overlay.show`.

**Config sections (分区块)**: render each config group as a distinct bordered card
(`.cfg-section` with title row + bottom border) so groups are visually separate
— not just an `<h2>` inside one flat card. Maps 1:1 to config groups (内核/LLM/Dashboard/飞书/微信).

**Model providers page (参考 9Router providers)**: a card grid (`grid-template-columns:repeat(auto-fill,minmax(200px,1fr))`), each card = icon+name+connection-status badge (`connected` green / `pending` red) + optional "默认" corner badge. Clicking a card (`onclick="editProvider(key)"`) → `prompt()` for API key → POST `/api/config`. Data driven from a `MODEL_PROVIDERS` list (`{key,name,ico,env,default,bg,desc}`); `env` = the gateway.env field that marks it "configured".

**⚠️ Per-panel forms need distinct `id`**: when splitting one config form into
multiple panels (配置/飞书/微信), each `<form>` must have a UNIQUE id
(`cfgform`, `cfgform-feishu`, `cfgform-wechat`) and `saveConfig(formId)` reads
`getElementById(formId)`. Duplicate `id="cfgform"` makes save only touch the first form.

## Feishu / WeChat channel integration (v0.3.6+)

Hermes kernel natively supports Feishu and WeChat as messaging platforms via
env vars read by their adapters:
- **Feishu** (`plugins/platforms/feishu/adapter.py`): `FEISHU_APP_ID`,
  `FEISHU_APP_SECRET`, `FEISHU_VERIFICATION_TOKEN` (验证码), `FEISHU_ENCRYPT_KEY`.
- **WeChat** (`gateway/platforms/weixin.py`): `WEIXIN_ACCOUNT_ID`, `WEIXIN_TOKEN` (验证码).

**Critical**: `gateway.env` is `source`d into the shell but its vars are NOT
exported to child processes. `cmd/main start` must **explicitly `export`** each
channel env var (with `:-` default) before `hermes gateway run`, else the
adapter never sees them:
```bash
export FEISHU_APP_ID="${FEISHU_APP_ID:-}"
export FEISHU_APP_SECRET="${FEISHU_APP_SECRET:-}"
export FEISHU_VERIFICATION_TOKEN="${FEISHU_VERIFICATION_TOKEN:-}"
export FEISHU_ENCRYPT_KEY="${FEISHU_ENCRYPT_KEY:-}"
export WEIXIN_ACCOUNT_ID="${WEIXIN_ACCOUNT_ID:-}"
export WEIXIN_TOKEN="${WEIXIN_TOKEN:-}"
```
Verify the adapter exists on the NAS (`find .../site-packages -path '*platforms*' -iname '*feishu*' -o -iname '*weixin*'`) — hermes v0.19.0 ships both.
