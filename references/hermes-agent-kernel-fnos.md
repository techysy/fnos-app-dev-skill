# Hermes Agent 内核打包 (hermes-core-fnos) — 完整经验

> 在 fnOS 上把 Hermes Agent 打包为独立内核应用 (Gateway API)，与 WebUI 前端包分离。2026-08 实战，仓库 techysy/hermes-core-fnos。

## 架构：两个包分离

```
fnOS 单机自闭环
┌─────────────────────────────────────────┐
│ Hermes Core  :8642  ← 本地内核/Gateway  │  (hermes-core-fnos)
│ Hermes WebUI :8787  ← 前端界面          │  (hermes-webui-fnos)
│   └─ WebUI 连本机 127.0.0.1:8642        │
└─────────────────────────────────────────┘
```

## 内核启动机制

- 内核 = `hermes gateway run`，监听 `0.0.0.0:8642`（API server 平台）
- **必须显式 `HERMES_HOME=/vol4/@appdata/<App>/hermes_home`**（fnOS 应用用户是 nologin，无 $HOME，不能依赖默认 ~/.hermes）
- `config.yaml` + `.env` 显式放 appdata，不用交互式 `hermes setup`

## 关键依赖与配置坑

1. **aiohttp 必需**：`pip install hermes-agent` 后还要 `pip install aiohttp`，否则 api_server adapter 不加载，8642 不监听（日志 `API Server: aiohttp not installed` / `No adapter available for api_server`）。

2. **config.yaml 需完整 custom_providers**：只有 `model.default` 不够，会报 `Unknown provider 'X'`。必须定义 provider 的 `base_url` + `api_key` + `models`。

3. **LLM 双通道设计**（用户明确要求）：
   - 9Router 专用：`router_api_key`（本机 :20128）
   - 通用兜底：`llm_base_url` + `llm_api_key` + `llm_model`（任意 OpenAI 兼容 API/直连）
   - 优先级：填了 `llm_base_url` 用兜底，否则 9Router

4. **9Router API key 需用户配置**：9Router 的 `/v1/models` 无需 key，但 `/v1/chat/completions` 需 key（requireApiKey）。数据库里 key 被脱敏存储（`<YOUR_API_KEY>`），无法恢复，必须用户填。

5. **venv 安装超时**：`pip install hermes-agent` 下载 50+ 依赖 ~100MB，需 1-2 分钟。SSH 60s 会中断；`--quiet` 吞错误难排查。对策：离线预打包 venv (`app/venv.tar.gz`) 秒装，或 install_callback 联网装（失败不阻断，cmd/main 做 hybrid 检测回退提示）。

## cmd/main 关键写法

- **BASH_SOURCE 定位兄弟脚本**：fnOS 1.1.31xx 的 `TRIM_APPDEST=/vol4/@appcenter/<App>`，但 cmd 脚本在 `/var/apps/<App>/cmd`。用 `CMD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` 定位同目录脚本（如 status_server.py），兼容各版本。
- **start 端口已占用跳过问题**：`start()` 若检测到端口已被监听会走 "already serving" 分支直接 return，**跳过副服务（状态页）启动**。restart 时旧内核进程没死透会触发。要先确保旧进程清干净。
- **status() 正确退出码**：running→0, stopped→1（fnOS 据此决定是否 start）。
- **cmd/main 以受限用户跑**：能建 venv/pip/绑端口（strava/metacubexd/9router 已验证），但手动 SSH 用 <user> 起的进程应用中心管不了。

## 状态页服务（解决手机 App 图标白屏）

fnOS 手机 App 用 **WebView iframe** 打开应用图标入口。入口若指向 JSON API（如 `/health`），iframe 无法显示 → `WebKitErrorDomain code=102`（frame load interrupted）白屏。

**修复**：加一个纯 stdlib 的极简 HTML 状态页服务（`status_server.py`，`http.server`，独立端口如 8648），入口 `app/ui/config` 指向它。显示内核 health/平台/版本。

## 跨用户 kill 限制

- SSH 的 <user>（Administrators 组）**无法 kill fnOS 应用用户进程**（`kill: Operation not permitted`）
- 残留进程（如被 stop 但没死透的 hermes gateway）只能由**应用中心**（应用用户）或 root 清理
- 遇到"端口被残留进程占、start 认为 running"时，让用户在应用中心先停止再启动
