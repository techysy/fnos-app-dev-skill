# Standalone Hermes Agent Kernel as an fnOS App (self-contained all-in-one)

> ⚠️ **2026-08-10 更新**：HermesWebUI 独立套件已废弃。HermesCore 升级为**自包含全能套件**——内置 `hermes dashboard` Web UI（默认开启 :9119），替代废弃的 HermesWebUI。用户只装 HermesCore 一个套件即可（内核 + 前端全搞定）。

Packaging the Hermes Agent kernel itself as a standalone fnOS app, now with built-in dashboard as the frontend.
Reference repo: https://github.com/techysy/hermes-core-fnos (v0.5.0+ self-contained, verified 2026-08).

## What it is

A self-contained fnOS app that installs `hermes-agent` into a python312 venv and runs:
- **Gateway API** (`hermes gateway run` → OpenAI-compatible `:8642`)
- **自研状态页仪表盘** (`status_server.py` → `:8648`, 纯 stdlib) — HermesCore 自己的前端，桌面图标入口
- **原生 Dashboard** (`hermes dashboard --skip-build` → `:9119`, default enabled) — Hermes 官方完整 Web UI，补充前端

```
fnOS
└── Hermes Core
    ├── Gateway (:8642)        ← kernel / Gateway (OpenAI-compatible API)
    ├── 自研状态页仪表盘 (:8648)  ← status_server.py = 桌面图标入口
    └── 原生 Dashboard (:9119)   ← hermes dashboard, 默认开启, 进阶 Web UI
```
两个前端都保留：桌面图标 → :8648 自研仪表盘；浏览器 → :9119 原生 dashboard。No remote server dependency.

## Key packaging facts (all verified on fnOS 1.1.31xx)

- **fnOS runs cmd/main as a dedicated nologin user** (e.g. `HermesCore`), with
  `TRIM_APPDEST=/vol4/@appcenter/<App>`, `TRIM_PKGVAR=/vol4/@appdata/<App>`, `PWD=/`.
  Evidence: strava app's diag log `USER=strava UID=969`.
- nologin users CAN build venvs, `pip install`, bind TCP ports, and write their own
  `/vol4/@appdata/<App>/` (strava/metacubexd/9router all prove this).
- **Do NOT rely on `$HOME`** (nologin users may have no home dir). Always set
  `export HERMES_HOME=${DATA_DIR}/hermes_home` explicitly.

## install_callback (venv + hermes-agent)

```bash
PY=/usr/bin/python3
[ -x /vol4/@appcenter/python312/bin/python3.12 ] && PY=/vol4/@appcenter/python312/bin/python3.12
"${PY}" -m venv "${VENV}"
"${VENV}/bin/pip" install --quiet pyyaml cryptography aiohttp || true
"${VENV}/bin/pip" install --quiet hermes-agent   # 50+ deps, ~100MB, 1-2 min
```

- **`aiohttp` is REQUIRED** for the api_server platform adapter. Without it:
  `WARNING gateway.run: API Server: aiohttp not installed` → port never listens.
- hermes-agent install needs network and 1-2 min. `--quiet` swallows errors — debug with a
  non-quiet manual run. Offer an **offline mode**: if `app/venv.tar.gz` exists, `tar xzf` it
  (seconds) instead of pip install.
- **Save wizard config in install_callback** (wizard/install fields arrive as `wizard_`-prefixed env):
  write `gateway.env` with `API_SERVER_*`, `ROUTER_API_KEY`, `LLM_*`.

## cmd/main start

```bash
export HERMES_HOME="${DATA_DIR}/hermes_home"
export API_SERVER_ENABLED=true
export API_SERVER_HOST="${API_SERVER_HOST:-0.0.0.0}"   # default 127.0.0.1 → LAN needs 0.0.0.0
export API_SERVER_PORT="${API_SERVER_PORT:-8642}"
export API_SERVER_KEY="${API_SERVER_KEY:-webui-gateway-key-2026}"
nohup "${VENV}/bin/hermes" gateway run >> "${LOG}" 2>&1 &
# poll /health with Bearer key until ready
```

- Health: `curl -H "Authorization: Bearer <key>" http://127.0.0.1:8642/health`
  → `{"status":"ok","platform":"hermes-agent","version":"0.19.0"}`
- `status()` must `return 1` when stopped (fnOS uses exit code to decide whether to call start).

## 自包含 dashboard 启用细节（v0.5.0 迭代, 2026-08）

HermesCore 内置 dashboard 作为前端（`:9119`），需在 cmd/main 里：

1. **`DASHBOARD_ENABLED` 默认改 `true`**：`[ "${DASHBOARD_ENABLED:-true}" = "true" ]`。原默认 false（纯后端内核），自包含后必须默认开。
2. **dashboard 密码持久化到 gateway.env**：未配置密码时自动生成随机密码，但要**写回 gateway.env**，否则每次重启密码都变（用户无法稳定登录）：
   ```bash
   if [ -z "${DASHBOARD_PASSWORD:-}" ]; then
       DASHBOARD_PASSWORD="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)"
       grep -q "^DASHBOARD_PASSWORD=" "$CONFIG_FILE" 2>/dev/null \
         && sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=\"$DASHBOARD_PASSWORD\"|" "$CONFIG_FILE" \
         || echo "DASHBOARD_PASSWORD=\"$DASHBOARD_PASSWORD\"" >> "$CONFIG_FILE"
   fi
   ```
3. **wizard/install 加「Dashboard 登录」步骤**（`wizard_dashboard_user` / `wizard_dashboard_password`），install_callback 写入 gateway.env 的 `DASHBOARD_USER`/`DASHBOARD_PASSWORD`。
4. dashboard 认证：cmd/main 的 write_config 在 `DASHBOARD_USER`+`DASHBOARD_PASSWORD` 都非空时写 `dashboard.basic_auth` 到 config.yaml。

## config.yaml — must define full custom_providers

A bare `model.default` is NOT enough. Without `custom_providers` the kernel errors:
`Unknown provider '...'`. Include base_url + api_key + models per provider.

## Dual-channel LLM connection (the important design)

Users do NOT all use 9Router — some connect any OpenAI-compatible API directly. Support both:

| mode | wizard/config fields | config.yaml provider |
|------|----------------------|----------------------|
| 9Router (local :20128) | `router_api_key` | 9Router Proxy, base_url `http://127.0.0.1:20128/v1` |
| generic fallback | `llm_base_url` + `llm_api_key` + `llm_model` | Custom LLM |

Priority in cmd/main write_config:
```
if LLM_BASE_URL set → model.provider = Custom LLM, model.default = LLM_MODEL
else                 → model.provider = 9Router Proxy, model.default = cbcn/deepseek-v4-flash
```

- 9Router `/v1/models` needs NO key, but `/v1/chat/completions` DOES (401 Invalid API key
  without it). The key is stored **masked** in its sqlite (`<<YOUR_API_KEY>>`), unrecoverable —
  so it MUST be a user-supplied wizard field.

## Wizard field prefix mapping (recurring)

- `wizard/install` fields → passed to **install_callback** as `wizard_<field>`.
- `wizard/config` (App settings page) fields → passed to **config_callback** as bare `<field>`.
- So install_callback persists install-time config; config_callback persists settings-page edits.
  Both write the same `gateway.env` that cmd/main sources.

## Verify a chat round-trip

```bash
curl -s -H "Authorization: Bearer <key>" -H "Content-Type: application/json" \
  http://127.0.0.1:8642/v1/chat/completions \
  -d '{"model":"cbcn/deepseek-v4-flash","messages":[{"role":"user","content":"hi"}]}'
```
Success returns `choices[0].message.content`.
