# DSH (DeepSeek Harness) for fnOS 打包经验

> 2026-08-13 打包 `@deepseek-ai/dsh`（DeepSeek 官方 agent）成 fnOS 应用，仓库 `techysy/dsh-fnos`。

## 核心：dsh 只绑 127.0.0.1，必须走官方统一网关

- **dsh web 拒绝 `--host 0.0.0.0`**（官方安全限制，报错：`intentionally not supported yet for safety: it would expose remote code execution to the network; use 127.0.0.1 instead`）
- 因此**不能**用 fnOS 端口服务（端口服务要绑 0.0.0.0），**必须**用飞牛官方统一网关 + 本地代理
- **dsh 有 browser-trust fence**（防 DNS rebinding），只信任回环地址 + `--trusted-host`；绑 127.0.0.1 时默认信任列表为空

## 架构

```
fnOS
└── dsh
    ├── dsh web (127.0.0.1:18080)  ← DeepSeek Harness 浏览器 UI (只回环)
    └── proxy.py (app.sock)         ← Python 代理, 统一网关 /app/dsh → 127.0.0.1:18080
```

- `app/ui/config`: `gatewayPrefix: /app/dsh` + `gatewaySocket: app.sock`
- `proxy.py`: 监听 `${TRIM_APPDEST}/target/app.sock`（AF_UNIX），HTTP 反向代理到 127.0.0.1:18080
  - **关键：重写 Host 头为 `127.0.0.1:18080`**，规避 dsh browser-trust（它检查 Host 防 rebinding）

## 启动命令

```bash
dsh web --host 127.0.0.1 --port 18080    # 常驻服务, 只回环
```

- `dsh` 命令（CLI 启动器）由 `npm install -g @deepseek-ai/dsh` 提供（532 个包，需联网 ~1min）
- 依赖 fnOS `nodejs_v24`（manifest `install_dep_apps = nodejs_v24`）

## 打包要点

- **manifest 必需**：`ICON.PNG` + `ICON_256.PNG`（根目录）+ `config/privilege`（`run-as: package`）+ `config/resource`（数据共享 dsh + dsh/data）+ `wizard/install`
  - 缺 `config/privilege` → fnpack 报 `Required file config/privilege is missing`
  - 缺 `ICON.PNG` → fnpack 报 `Required file ICON.PNG is missing`
- **desktop_applaunchname 与 app/ui/config 的 key 必须一致**：`dsh.Application` ↔ `"dsh.Application"`
- **DSH_HOME**：`${DATA_DIR}/dsh_home`（profiles + logs），安装时提前建避免时序问题
- **DeepSeek API Key**：写 `DSH_HOME/.env`（`DEEPSEEK_API_KEY=sk-xxx`）
- 独立版本号（1.0.0，不随上游同步）

## 验证

- 本地：`dsh web --host 127.0.0.1 --port 18080` → `curl http://127.0.0.1:18080/` 200，页面含 `window.__DSH_BOOT__`（SPA）
- 代理链路：`curl --unix-socket <app.sock> http://localhost/` → 200（模拟统一网关）
- fpk 产物（`tar tzf`）应含 app.tgz / cmd/ / config/ / ICON*.PNG / manifest / wizard/

## 相关

- `references/fnos-unified-gateway-microapp.md`：fnOS 官方统一网关机制（gatewayPrefix/gatewaySocket/WebSocket）
- `references/hermes-core-kernel-fnos.md`：HermesCore 打包（Gateway + Web UI + 统一网关），本套件同思路
