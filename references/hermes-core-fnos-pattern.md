# Hermes Core on fnOS — 本地内核部署与状态页模式

Hermes Agent 本地内核作为独立 fnOS 应用（hermes-core-fnos）的完整部署模式，以及与前端 WebUI 包的"两包分离"自闭环方案。

## 架构（自闭环，不依赖远程）

```
fnOS (单机)
┌─────────────────────────────────────────┐
│ Hermes Core  :8642  ← 本地内核/Gateway  │
│   └─ hermes gateway run                 │
│   └─ venv 装 hermes-agent               │
│   └─ 连本机 9Router :20128 / LLM        │
│ Hermes Core  状态页 :8648 (HTML)        │
│ Hermes WebUI :8787  ← 前端界面          │
│   └─ 连 127.0.0.1:8642                  │
└─────────────────────────────────────────┘
```

## 本地内核在 fnOS 的关键配置

- **`HERMES_HOME` 必须显式指向 `/vol4/@appdata/<App>/hermes_home`**。fnOS 应用用户是 nologin，可能无 `$HOME` 目录，不能依赖系统 HOME。
- **`hermes gateway run` 即 API server**（监听 `API_SERVER_PORT`，默认 8642）。`/v1/chat/completions` 提供 OpenAI 兼容端点，供 WebUI 前端连。
- **`API_SERVER_*` 环境变量**：`API_SERVER_HOST=0.0.0.0`（局域网可达）、`API_SERVER_PORT`、`API_SERVER_KEY`（Bearer 鉴权，**即使是 loopback 也必须设置**）。
- **api_server 平台需要 aiohttp**：缺 aiohttp 时 `gateway run` 日志 `API Server: aiohttp not installed` → `No adapter available for api_server`，8642 不监听。需 `pip install aiohttp`。
- **config.yaml 必须含完整 `custom_providers`**（含 base_url + api_key + models）。只有 `model.default` 而无 provider 定义会报 `Unknown provider 'xxx'`。

## LLM 连接双通道（wizard / 应用设置页配置）

为兼容"不一定用 9Router 也可能直连"，提供两套字段：

| 字段 | 说明 |
|------|------|
| `router_api_key` | 9Router API Key（本机 :20128）。填了则用 9Router。 |
| `llm_base_url` + `llm_api_key` + `llm_model` | 通用兜底 — 任意 OpenAI 兼容 API（直连/代理） |

`cmd/main` 的 `write_config` 里根据 `LLM_BASE_URL` 是否填写决定 `model.default` 指向 `Custom LLM`（兜底）还是 `9Router Proxy`。

## 9Router API Key 需要用户配置

- 9Router `/v1/models` 不需要 key，但 `/v1/chat/completions` **需要 API key 鉴权**（requireApiKey）。
- 数据库 `apiKeys` 表里 key 被**脱敏存储**（如 `<YOUR_API_KEY>`），无法恢复完整 key。
- **必须由用户在安装向导/应用设置页填 `router_api_key`**。

## 状态页服务（修复手机 App iframe 错误）

手机 fnOS App 用 WebView iframe 加载应用入口。若入口指向 JSON API 端点（如 `/health`），iframe 无法渲染 JSON → `WebKitErrorDomain code=102`（frame load interrupted）。

**修复**：新增纯 stdlib `status_server.py`（`http.server.ThreadingHTTPServer` + `allow_reuse_address=True`），监听独立端口（8648），返回内嵌目标服务 health 探测的极简 HTML 状态页。`cmd/main` 的 `start` 内核就绪后启动它，`stop` 一并停止；入口 `app/ui/config` 指向 `:8648/`。

状态页显示：内核健康状态、平台、版本、端口、API 地址。核心逻辑：

```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class Server(ThreadingHTTPServer):
    allow_reuse_address = True
def _core_health():
    # urllib.request GET http://127.0.0.1:8642/health with Bearer key
    # 返回 (ok, info_json)
```

## fnOS 应用生命周期脚本要点

- `cmd/main` 的 `status()` 停止分支必须 `return 1`（非 0），否则 fnOS 永不调 start。
- 启动用 `nohup <bin> ... >> log 2>&1 &`，PID 写文件。
- stop 用 `pkill -f <实际 cmdline>` 兜底防孤儿进程占端口（cmdline 匹配要与真实进程一致）。
- install_callback 建 venv：优先 fnOS python312 运行时 `/vol4/@appcenter/python312/bin/python3.12`，否则系统 python3。
- 支持离线：若 `app/venv.tar.gz` 存在则解压复制（秒装），否则在线 pip install（`hermes-agent` 50+ 依赖，1-2 分钟）。
- **已安装应用的 `cmd/` 和安装目录是 root 只读**，SSH 无法直接改，必须重打包 + 应用中心重装。运行时数据放 `/vol4/@appdata/<App>/`（应用用户可写）。

## 相关仓库

- `techysy/hermes-core-fnos` — 本地内核包（服务端）
- `techysy/hermes-webui-fnos` — WebUI 前端包（连接端，默认连 `127.0.0.1:8642`）

## 内置聊天窗口 vs 飞书/微信消息（架构事实，2026-08 调研 + 建成）

**已建成**（2026-08）：消息平台设置面板（v0.4.7）→ 微信扫码登录（v0.4.7.1-test）。

- **内置聊天窗口是单向主动对话**：通过本机 `api_server` (8642) 的 `/v1/chat/completions` 代理，用户发起 → 内核响应。**与飞书/微信渠道无关**，不做消息双向同步。
- **status_server.py 里有 `FEISHU_*`(APP_ID/APP_SECRET/VERIFICATION_TOKEN/ENCRYPT_KEY) 和 `WEIXIN_*`(ACCOUNT_ID/TOKEN) 字段定义 + `_form_fields_feishu()`/`_form_fields_wechat()` 函数，但 `_form_fields()` 只渲染 `core`+`dash` 分组**——消息渠道字段存在但 UI 无入口（0.4.0 起移除消息渠道面板）。
- **Hermes 能发飞书/微信**（`send_message` 工具，`tools/send_message_tool.py`）：
  - **飞书**：经 `hermes-lark-streaming`/`feishu_platform` 插件，target 形如 `feishu:oc_xxx:ou_xxx`
  - **微信(weixin)**：**仅需 `.env` 的 `WEIXIN_TOKEN`+`WEIXIN_ACCOUNT_ID` 即可**，无需 gateway.yaml 段（send_message_tool 会合成 pconfig）。`WEIXIN_HOME_CHANNEL` 设家频道。
- **微信 QR 扫码登录（原生 iLink 机制）**：`gateway.platforms.weixin.qr_login()` 是交互式函数（打印 ASCII 二维码 + 轮询 480s），不适合直接嵌入 Web UI。**拆分为两个 HTTP 端点**更干净：
  - `POST /api/weixin/qr/start` → 用 weixin adapter 的 `_api_get(session, ILINK_BASE_URL, EP_GET_BOT_QR)` 拿 `{qrcode_value, qrcode_url}`（`qrcode_url` 是 `https://liteapp.weixin.qq.com/q/...` 可被微信扫的 URL）
  - `GET /api/weixin/qr/status?qrcode=...` → 轮询 `EP_GET_QR_STATUS`；`status=="confirmed"` 时读 `ilink_bot_id`/`bot_token`/`baseurl`，**写 gateway.env**（`WEIXIN_ACCOUNT_ID`/`TOKEN`/`BASE_URL`/`CDN_BASE_URL`）
  - 前端：按钮 → 显示二维码（在线 QR 服务如 `api.qrserver.com/create-qr-code/?data=<url>` 渲染，或给 liteapp 链接）→ 每 2s 轮询 → confirmed 提示重启
  - **import 注意**：status_server 是纯 stdlib，需把应用 venv 的 `site-packages` 加入 `sys.path` 才能 import `gateway.platforms.weixin`（venv 里装了 hermes-agent）；不可用时 try/except 优雅降级提示
- **飞书无扫码机制**：飞书机器人只能通过「企业自建应用」的 App ID + Secret 连接（`lark.Client.builder().app_id().app_secret()`），**没有 QR 扫码登录**。所以飞书面板保持手动填 App ID/Secret，加引导文案即可。
- **NAS 网关接线**：cmd/main 已 `export FEISHU_*`/`WEIXIN_*` env 给网关；微信用内置适配器（env 自动启用，`WEIXIN_TOKEN`+`ACCOUNT_ID` 设了就自动连）；飞书需 `setup_plugins` 自动 `hermes plugins install` hermes-lark-streaming 插件（来源 gitee.com/Aowen-Nowor/hermes-lark-streaming）。
- **读入站消息**：`/api/sessions` 返回 `source: feishu`/`source: weixin` 的会话列表（含 preview/message_count），可轮询展示。

> ⚠️ **第三方插件卡片截断不是 HermesCore 的 bug**：飞书回复经 `hermes-lark-streaming` 插件渲染成流式卡片，长内容会被插件自身限制截断（推理文本 2000 字符 `_REASONING_DISPLAY_LIMIT`、长文本 2400 字符分块 `_MAX_CHUNK_CHARS`、飞书 200 元素卡片硬限 `_enforce_card_element_limit`）。要改需 patch 插件源码（会偏离上游）或反馈作者，不在 HermesCore 打包代码里解决。
