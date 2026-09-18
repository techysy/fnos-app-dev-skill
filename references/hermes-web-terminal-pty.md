# Hermes 内置 Web 终端 / PTY 机制（在 fnOS 套件里做终端功能的钥匙）

> 调研自 2026-08-10 在 HermesCore 自包含套件上实现"自研状态页（:8648）升级为真终端"的需求。结论：**Hermes 官方已内置完整 Web 终端，复用它是正解，别自己从零写。**

## 核心事实

### 1. Hermes 官方 dashboard 的 chat tab 就是 Web 终端
`hermes dashboard`（后端 = `hermes serve` / `web_server.py`，默认 :9119）的 **chat tab 已是一个完整 Web 终端**：浏览器 xterm.js + 后端 PTY + 原生 Hermes CLI，体验和命令行一致。

实现：
- `hermes_cli/pty_bridge.py` — `PtyBridge`（POSIX PTY 包装，`ptyprocess` 驱动）
- `web_server.py` `/api/pty` WebSocket endpoint — 双向桥（PTY → ws bytes / ws bytes → PTY）
- spawn 的是 `hermes --tui`（见 `_resolve_chat_argv` / `_make_tui_argv`）

### 2. WebSocket 终端协议（/api/pty）
- 浏览器 → 服务器：文本/二进制（键盘输入）；特殊 resize 消息 `\x1b[...t`（`_RESIZE_RE`）在本地消费，写 PTY 用 `TIOCSWINSZ`
- 服务器 → 浏览器：二进制（PTY 原始 ANSI 输出）
- `PtyBridge.spawn(argv, cwd, env)` spawn 终端进程

### 3. ⚠️ 两种"原生 Hermes 终端"的 node 依赖区别（关键决策点）
| 命令 | 类型 | node 依赖 | 说明 |
|------|------|----------|------|
| `hermes --tui` | Node.js TUI（`node dist/entry.js`） | ✅ **需要 node** | Hermes 官方 /api/pty 用的就是它 |
| `hermes chat` | Python 交互式 CLI（readline/prompt_toolkit） | ❌ **不需要** | 纯 Python 交互终端 |

- fnOS 上用 `--tui` 需 `install_dep_apps=nodejs_v24`；用 `hermes chat` 则零 node 依赖
- 若要在自研/纯 stdlib 服务里加真终端且不想引 node，**spawn `hermes chat`（Python CLI）** 是规避 node 的路径

### 4. 复用 pty_bridge 的前提
- `pty_bridge` 依赖 `ptyprocess`（Hermes venv 自带，`pip show ptyprocess`）
- 要让 status_server 之类 import 它，**必须用 Hermes venv 的 python 跑**（`${VENV}/bin/python`），不是系统 `/usr/bin/python3`
- `status_server.py` 在 cmd/main 里已优先 `${VENV}/bin/python` 启动（`[ -x "${VENV}/bin/python" ] && PY="${VENV}/bin/python"`）

## 在纯 stdlib 服务（如 HermesCore status_server :8648）加真终端的实现路径

选项（从省事到重）：
1. **iframe 嵌入 :9119 chat tab**（最省事，完全复用官方终端）——在 :8648 加「终端」tab iframe `http://127.0.0.1:9119/chat`
2. **自研 WebSocket + PTY，spawn `hermes chat`（Python CLI）**——规避 node，但需手写 stdlib WebSocket（HTTP Upgrade + 帧解析 ~100 行）+ 复用 pty_bridge + xterm.js CDN
3. **自研 WebSocket + PTY，spawn `hermes --tui`（Node TUI）**——完全对齐官方 /api/pty 体验，但需 node

HermesCore 的 status_server.py 是 `ThreadingHTTPServer`（纯 stdlib），加 WebSocket 需处理 HTTP Upgrade 后脱离 handler 用独立线程管理长连接。

## 前端 xterm.js
- xterm.js 浏览器端渲染 ANSI（`web_server.py` 注释明确：浏览器通过 xterm.js 渲染）
- 可 CDN 加载（需外网）或本地打包进 fpk

## 相关
- `references/hermes-core-kernel-fnos.md`：HermesCore 自包含全能套件（内核 :8642 + 自研状态页 :8648 + 原生 dashboard :9119）
- Hermes 源码位置（本地开发参考）：`~/.hermes/hermes-agent/hermes_cli/pty_bridge.py`、`web_server.py`（/api/pty 在 ~11505 行附近）
