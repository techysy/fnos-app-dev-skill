# 静态文件 App 打包模式 (fnOS)

适用于纯前端 Web 应用（无后端运行时依赖），如 MetaCubeXD (Mihomo Dashboard)、Clash Dashboard 等。

## Windowed vs Fullscreen (url vs iframe)

fnOS 应用有两种入口模式，可以同时打包两个版本的 fpk：

| 模式 | config `type` | 行为 | fpk 后缀 |
|---|---|---|---|
| **Fullscreen** | `"url"` | 新浏览器标签页打开（全屏体验） | 默认（无后缀） |
| **Windowed** | `"iframe"` | fnOS 桌面窗口内打开（可最大化） | `-iframe` |

### 切换方式

修改 `app/ui/config` 中的 `type` 字段：

```json
// 全屏版（默认）
{ ".url": { "app.Application": { "type": "url", ... } } }

// 窗口化版
{ ".url": { "app.Application": { "type": "iframe", ... } } }
```

### 双版本打包流程

```bash
# 1. 打 iframe 版
sed -i 's/"type": "url"/"type": "iframe"/' app/ui/config
fnpack build && cp app.fpk app-iframe.fpk

# 2. 打 url 版（默认）
sed -i 's/"type": "iframe"/"type": "url"/' app/ui/config
fnpack build
```

两个 fpk 发布到同一个 GitHub Release，用户按需下载。

## Preparation

```bash
# 1. Download the static dist
curl -sL https://github.com/<org>/<repo>/releases/download/<tag>/compressed-dist.tgz | tar xz -C app/www/

# 2. Edit config to point to your backend API
cat > app/www/config.js << 'EOF'
window.__CONFIG__ = { defaultBackendURL: 'http://<NAS_IP>:9090' }
EOF

# 3. Extract icon from PWA icons
python3 -c "
from PIL import Image
img = Image.open('app/www/pwa-512x512.png')
img.resize((64,64), Image.LANCZOS).save('ICON.PNG')
img.resize((256,256), Image.LANCZOS).save('ICON_256.PNG')
"
```

## cmd/main pattern

```bash
#!/bin/bash
set -euo pipefail
APP_DIR="${TRIM_APPDEST:-/var/apps/${APP_NAME}}"
# Dual-path detection
if [ -d "${APP_DIR}/www" ]; then WWW_DIR="${APP_DIR}/www"
elif [ -d "${APP_DIR}/target/www" ]; then WWW_DIR="${APP_DIR}/target/www"
else echo "ERROR: www dir not found" >&2; exit 1; fi

PORT="${TRIM_SERVICE_PORT:-9091}"
# Python http.server — hash-route SPAs (#/) don't need SPA fallback
nohup /usr/bin/python3 -m http.server "${PORT}" --bind 0.0.0.0 \
    --directory "${WWW_DIR}" >> "${LOG}" 2>&1 &
```

**Why Python http.server works for SPAs:** Hash-route SPAs (`#/path`) never hit the server with sub-paths — all navigation is client-side. Every request is for `/` or static assets.

## Runtime Config Pattern (wizard/config + sed)

Let users change backend API from App Center settings without rebuilding fpk.

### wizard/config

```json
[{ "stepTitle": "连接配置", "items": [
  { "type": "text", "field": "api_url", "label": "API 地址",
    "initValue": "http://<NAS_IP>:9090", "rules": [{"required": true}] }
]}]
```

### config_callback

```bash
#!/bin/bash
DATA_DIR="${TRIM_PKGVAR:-/vol4/@appdata/${APP_NAME}}"
mkdir -p "${DATA_DIR}"
echo "${api_url:-http://<NAS_IP>:9090}" > "${DATA_DIR}/api_url"
exit 0
```

### cmd/main reads config

```bash
apply_config() {
    local api_url
    [ -f "${DATA_DIR}/api_url" ] && api_url=$(cat "${DATA_DIR}/api_url" | tr -d '[:space:]')
    api_url="${api_url:-http://<NAS_IP>:9090}"
    [ -f "${WWW_DIR}/config.js" ] && sed -i "s|defaultBackendURL: '[^']*'|defaultBackendURL: '${api_url}'|g" "${WWW_DIR}/config.js"
}
```

**wizard/config field values:** Unlike `wizard/install` (which prefixes `wizard_`), `wizard/config` passes field values as **bare env var names** to `config_callback`. `field: "api_url"` → `${api_url}`, NOT `${wizard_api_url}`.

## Comparison: static vs Node.js vs Python web

| Pattern | Runtime | fpk size | Use case |
|---|---|---|---|
| **Static + Python http.server** | None | 2-5MB | Pure frontend SPA, hash-route |
| **Node.js standalone** | nodejs_v24 | 10-20MB | Next.js/Nuxt SSR |
| **Python web server** | python312 | 5-15MB | Flask/FastAPI backend |
