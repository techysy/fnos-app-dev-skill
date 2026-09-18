# 本地内核 fnOS 应用包模式（hermes-core-fnos 参考）

将 Hermes Agent 内核打包成独立 fnOS 应用（模式 B / 自闭环），供 WebUI 等前端连本机 Gateway。
参考仓库：https://github.com/techysy/hermes-core-fnos

## 架构

```
fnOS (单机自闭环)
┌─────────────────────────────────────────┐
│ Hermes WebUI  :8787   ← 前端界面 (url 新标签页)│
│   └─ 连 127.0.0.1:8642                  │
│ Hermes Core   :8642   ← 本地内核/Gateway │
│   └─ hermes gateway run                 │
│       └─ 本地 venv hermes-agent         │
│           └─ LLM (9Router :20128 / 兜底) │
└─────────────────────────────────────────┘
```

关键：`hermes gateway run` 本身承载 **API server (8642) + 消息平台 + cron 调度**。重启内核 = 重启整个 gateway（含消息网关）。

## 内核包 cmd/main 要点

- `HERMES_HOME=/vol4/@appdata/<App>/hermes_home`（显式指定，不依赖 $HOME，因为 fnOS 应用用户是 nologin 可能无 home 目录）
- `DATA_DIR=${TRIM_PKGVAR:-/vol4/@appdata/<App>}`（必须用 fnOS 标准数据目录，不是 `${APP_DIR}/var`）
- 启动：`nohup $VENV/bin/hermes gateway run` + 健康检查轮询 `curl /health`（需 `Authorization: Bearer <API_SERVER_KEY>`）
- API server 需要环境变量：`API_SERVER_ENABLED=true`、`API_SERVER_HOST=0.0.0.0`、`API_SERVER_PORT`、`API_SERVER_KEY`
- 纯后台服务：`checkport=false`（避免 fnOS 端口检查误判），`ctl_stop=true`（应用中心启停）

## install_callback（两种模式）

A) 在线：建 venv + `pip install hermes-agent aiohttp`（hermes-agent 依赖 ~50+ 个包，1-2 分钟，可能超时）
B) 离线：预打包 venv（`app/venv.tar.gz`，~150MB），解压即用免联网

install_callback 里 `pip install --quiet` 会吞掉错误难排查，排障时手动非 quiet 跑。

## config.yaml 必须含完整 custom_providers

只有 `model.default` 会报 `Unknown provider 'xxx'`。必须定义：
```yaml
model:
  default: <model>
  provider: <provider-name>
custom_providers:
  - name: <provider-name>
    base_url: <url>
    api_key: <key>
    models: [<model-a>, <model-b>]
```

## 双通道 LLM 连接（用户偏好）

用户不一定用 9Router，可能直连任意 API。提供两套配置（wizard/网页均可配）：
- `ROUTER_API_KEY` — 9Router 专用（本机 :20128）
- `LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL` — 通用兜底（任意 OpenAI 兼容 API）
- 优先级：填了 `LLM_BASE_URL` 用兜底（Custom LLM provider），否则用 9Router，都不填默认 9Router

9Router `/v1/models` 不需要 key，但 `/v1/chat/completions` **需要 API key**（requireApiKey）。key 存数据库是脱敏的（`<YOUR_API_KEY>`）无法恢复，必须由用户配置。

## 状态页 + 网页配置（cmd/status_server.py）

fnOS 桌面图标入口不能指向 JSON API 端点（会 iframe 白屏）。提供一个纯 HTML 状态页服务：
- 纯 Python stdlib（http.server）零依赖，监听独立端口（如 8648）
- `GET /` → HTML 状态页（内核/消息网关/兜底 LLM 状态 + 配置表单）
- `POST /api/config` → 保存 gateway.env（Bearer API key 鉴权）
- `POST /api/restart` → 调 `cmd/main restart` 重启内核（Bearer 鉴权，`subprocess.Popen` 后台不阻塞）
- 敏感字段脱敏显示（前后几位 + ...）

状态数据来源：
- 内核健康：`GET /health` → `{status, platform, version}`
- 消息网关：`GET /health/detailed` → `gateway_state` + `platforms` dict（各平台 state=connected 在线）
- 兜底 LLM：探测 `<LLM_BASE_URL>/v1/models`（带 key），显示连接正常/失败/未配置 + 可用模型

## 三种配置方式

安装向导（wizard/install）/ 应用设置页（wizard/config）/ 状态页网页。网页最直观。

wizard 字段前缀映射（易错）：
- `wizard/install`（安装向导）字段以 `wizard_` 前缀传给 **install_callback**（如 `wizard_router_api_key`）
- `wizard/config`（应用设置页）字段以**裸名**传给 **config_callback**（如 `router_api_key`）
- install_callback 负责保存安装向导配置到 gateway.env，config_callback 负责保存应用设置页配置

## 跨用户残留进程无法 kill（关键坑）

**现象**：SSH 用户（<user>）无法 kill fnOS 应用用户（HermesCore uid）的进程，报 `Operation not permitted`。
- 手动 `cmd/main restart` 时 stop 杀不掉应用用户进程 → 端口仍被占 → start 认为"已在运行"跳过后续启动（如状态服务）
- 残留状态服务占端口，新版无法启动（端口冲突）

**对策**：
- 残留进程只能由**应用中心**（以应用用户运行）或 **root** 清理
- 让用户在应用中心"先停止再启动"，能正确清掉残留
- 测试新版时**换不同端口**（如 8649）避免与残留冲突

## 手动启动污染 venv 属主

用 SSH 用户（非应用用户）手动 `cmd/main start` 会以错误属主创建数据目录文件（venv/state 归 <user>），导致**应用中心（应用用户）无法访问** → 应用中心启动失败（白屏/stopped）。修复：`chown -R <AppUser>:<AppUser> /vol4/@appdata/<App>/<venv> <hermes_home> <state>`。**测试完必须恢复属主，或直接在应用中心启停。**

## cmd/main 定位同目录脚本用 BASH_SOURCE

fnOS 1.1.31xx 的 `TRIM_APPDEST=/vol4/@appcenter/<App>`，但 lifecycle 脚本实际在 `/var/apps/<App>/cmd/`（fnOS 调用点）。不能用 `${APP_DIR}/cmd/` 找同目录文件（如 status_server.py），会找不到。正确：
```bash
CMD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```
获取 cmd/main 自身所在目录，同目录文件就在旁边。兼容各 fnOS 版本。

## 版本迭代

小步迭代（v0.1.0 → v0.2.x），每次改一个点，CHANGELOG 记录。manifest 版本号与 CHANGELOG 同步。
