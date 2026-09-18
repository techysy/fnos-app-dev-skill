# fnOS 官方统一网关（gateway-registration / microApp）机制

> 来源：fnOS 官方 developer 文档 `https://developer.fnnas.com/docs/core-concepts/gateway-registration`（2026-08 调研）。
> 用途：当 fnOS 套件需要"复用系统访问域名 + 常驻服务 + 支持 WebSocket + 提供 API"时，用统一网关，而不是自研裸端口/WebSocket。

## 能力对比（官方三种访问模型）

| 能力 | index.cgi | **统一网关** | 端口服务 |
|------|-----------|------------|---------|
| 简单静态页面 | 适合 | 支持 | - |
| 常驻服务 | 不推荐 | **适合** | 适合 |
| WebSocket | **不支持** | **支持** | - |
| NAS 登录态 | CGI 前校验 | **转发前校验 + 用户 Header** | 不接入登录态 |
| 性能 | 每次启动 CGI | 转发到长期服务 | - |
| 常见路径 | /cgi/ThirdParty/{app}/index.cgi/ | **/app/{app}** | 独立端口 |

## 工作原理

1. 应用通过 `gatewayPrefix` 注册公开路径（如 `/app/myapp`）
2. 应用服务监听 `gatewaySocket` 声明的 **Unix Socket**（`app.sock`，放 `${TRIM_APPDEST}/target/`）
3. fnOS 校验用户会话 → 把 HTTP/WebSocket 请求转发到 `/var/apps/<app>/target/app.sock`
4. 应用读取网关转发的用户 Header 获取身份上下文

## 入口配置（app/ui/config）

```json
{
  ".url": {
    "hermescore.main": {
      "title": "Hermes Core",
      "icon": "images/icon_{0}.png",
      "type": "iframe",
      "protocol": "",
      "gatewayPrefix": "/app/hermescore",
      "gatewaySocket": "app.sock",
      "url": "/app/hermescore",
      "allUsers": true
    }
  }
}
```

- `protocol` 和 `port` **会被忽略**，不参与统一网关路由
- `gatewaySocket` 只填 Socket 文件名（`app.sock`），Socket 放已安装应用的 target 目录（脚本用 `${TRIM_APPDEST}` 定位）

## 会话校验 + 用户 Header（网关转发到应用）

| Header | 说明 | 示例 |
|--------|------|------|
| `X-Trim-Userid` | 当前用户 UID | 1000 |
| `X-Trim-Isadmin` | 是否管理员 | true/false |
| `X-Trim-Username` | 当前用户名 | admin |

- 网关校验登录状态，**不负责业务权限**；应用仍要自己校验数据归属/管理接口/高风险操作
- 不要信任客户端传入的用户 ID，用网关转发的 Header

## WebSocket（官方原生支持）

- WebSocket 复用同一个 gatewayPrefix + Socket，建议放稳定子路径，如 `/app/myapp/ws`
- **HTTP 和 WebSocket 路由都应保持在声明的 gatewayPrefix 下**

```javascript
const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
const wsUrl = `${wsProtocol}//${location.host}/app/myapp/ws`;
const socket = new WebSocket(wsUrl);
socket.onopen = () => socket.send(JSON.stringify({ type: "ping" }));
```

- 通过网关建立的 WebSocket 连接，建立时获得同样的身份上下文；连接后绑定到 `X-Trim-Userid`
- Docker 应用也可用：把 `${TRIM_APPDEST}` 挂载进容器，服务在该目录创建 socket

## ⚠️ 关键认知（2026-08-10 调研）

- **统一网关是"访问层"优化**：提供官方 URL（`/app/{app}`）、官方鉴权（会话 + 用户 Header）、官方 WebSocket 传输（代理）。**但 WebSocket 帧解析仍需应用自己处理**（后端在 Unix socket 上处理 HTTP Upgrade + 帧解析），fnOS 网关做的是把客户端 WebSocket 连接代理到 Unix socket。
- **应用要监听 Unix socket**：Python `http.server` / `ThreadingHTTPServer` 可绑定 Unix socket（`server_address = socket_path`），但 WebSocket 握手/帧仍需自己实现（stdlib ~100 行）或用库。
- 参考案例：fnOS 官方 `fygo-browser` 套件用 `gatewaySocket: "app.sock"` + `gatewayPrefix: "/app/fygo-browser"`，由 Go 二进制监听 socket。
- **用官方统一网关 vs 自研裸端口**：要"复用系统访问域名 + 接入登录态 + WebSocket" → 用统一网关；要"独立端口不接登录态" → 用端口服务。

## 相关

- `references/hermes-web-terminal-pty.md`：Hermes 内置 Web 终端/PTY（pty_bridge + /api/pty WebSocket），可配合统一网关做终端。
- `references/hermes-core-kernel-fnos.md`：HermesCore 自包含全能套件架构。
- trim-cli（飞牛官方 CLI skill）：系统/应用管理，不涉及 Web 终端嵌入。
