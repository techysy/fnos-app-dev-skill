# fnOS 自包含 Hermes Agent 应用打包（HermesWebUI 自包含版 / route A）

把 Hermes WebUI 打包成**自包含完整版**：一个套件同时带前端（server.py）+ 后端（Hermes Agent Gateway），不依赖 HermesCore / trim.hermes。

## 架构

```
HermesWebUI (自包含)
├── Gateway (Hermes Agent)  →  :8642  (hermes gateway run, aiohttp API server)
└── server.py 前端          →  :8787  (连本机 :8642 gateway)
```

双进程共享 `HERMES_HOME`。前端是服务入口（健康检查以 8787 为准）。

## 关键事实（2026-08 实测验证）

### 1. 必须声明 python312 运行时依赖
Hermes Agent 的 C 扩展（aiohttp/yaml/pydantic_core 等）是 **cp312** 编译，必须用 Python 3.12 建 venv。

- manifest: `install_dep_apps = python312`（fnOS 官方支持的运行时依赖名，同 nodejs_v24/go-1.26）
- venv 必须用 `/vol4/@appcenter/python312/bin/python3.12`，**不能用系统 `/usr/bin/python3`（fnOS 上默认是 3.11）**
- HermesCore 的 install_callback 用 `[ -x /vol4/@appcenter/python312/bin/python3.12 ] && PY=...` 检测

### 2. 必须额外 pip install aiohttp ⚠️（最容易踩的坑）
`pip install hermes-agent` 默认**不含 aiohttp**。缺了它，gateway 日志会报：
```
WARNING gateway.run: API Server: aiohttp not installed
WARNING gateway.run: No adapter available for api_server
```
**这不是 false positive** —— API server 真的起不来，端口不监听。必须：
```bash
pip install pyyaml cryptography aiohttp
pip install hermes-agent
```

### 3. API_SERVER_KEY 必须 >=16 字符
gateway 对 API server 有安全校验，key 太短（或 placeholder）直接拒绝启动：
```
ERROR gateway.platforms.api_server: Refusing to start: API_SERVER_KEY is a placeholder or too short (<16 chars)
```
生成强 key：`openssl rand -hex 16`。install_callback/cmd/main 需在无 key 时自动生成并写入 gateway.env。

### 4. config.yaml 需要 api_server 段 + .env
- `HERMES_HOME/config.yaml` 需含 `api_server: {enabled: true, host, port}`
- `HERMES_HOME/.env` 需含 LLM provider keys
- gateway 首次启动才创建 state.db，健康检查可能有几秒延迟

## cmd/main 生命周期要点

- `ensure_venv()`：检测 `venv/bin/hermes` 存在即跳过；否则 python312 建 venv + pip install（在线模式；可加 `--proxy http://127.0.0.1:7890` fallback）
- `start_gateway()`：配置 API_SERVER_* 环境变量 → `nohup hermes gateway run`，健康检查轮询 `curl -H "Authorization: Bearer $KEY" :port/health`
- `start_webui()`：`nohup python server.py`，设 `HERMES_WEBUI_GATEWAY_BASE_URL=http://127.0.0.1:8642` + `HERMES_WEBUI_GATEWAY_API_KEY`
- `stop()`：先停 server.py，再停 gateway（pkill 多种 cmdline 兜底）
- `DATA_DIR` 默认必须 `/vol4/@appdata/<App>`（不是 `${APP_DIR}/var`，那是只读安装目录）
- 进程必须由 App Center 启动（app 用户），别用 SSH 手动 start（会以错误用户/端口残留）

## 端口冲突注意
自包含 gateway 用 8642，和 HermesCore 相同。自包含版不依赖 HermesCore，建议用户二选一，或改 gateway 端口。

## 依赖清单速查（运维/移植参考）
| 层 | 依赖 | 声明位置 |
|----|------|---------|
| fnOS 运行时 | `python312` | manifest `install_dep_apps` |
| pip | `hermes-agent`（自带 70+ 传递依赖）| install_callback `pip install` |
| pip | `aiohttp`（必需！）| install_callback `pip install` |
| pip | `pyyaml` `cryptography` | install_callback `pip install` |
| 外网 | PyPI 可访问 | 安装时联网 1-2 分钟 |
