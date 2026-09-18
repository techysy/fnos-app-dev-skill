# HermesWebUI 套件废弃决策记录（2026-08-10）

> 决策：**废弃 HermesWebUI 这个独立套件应用，不再发布。**
> 自包含 Hermes Agent（`hermes dashboard`，v0.19.0 起）本身已是完整 Web UI，可替代独立 WebUI 前端，无需再单独打包 HermesWebUI 套件。

## 废弃范围

- **GitHub 仓库** `techysy/hermes-webui-fnos` → 归档（archived），不再维护。
- **交付 fpk** `/vol1/1000/fnOS App/fpk/HermesWebUI/` → 删除（含 2.0.0 url 版 + 2.0.0-iframe 窗口版）。
- **历史 fpk** `/vol1/1000/fnOS App/old_fpk/HermesWebUI/` → 删除（12 个：0.52.x ~ 1.0.1）。
- **NAS 残留空目录** `/vol4/@appdata/HermesWebUI`、`@appconf`、`@apphome`、`@appmeta` → 删除（套件卸载后残留，均已空）。
- **临时备份** `/vol4/1000/SSD/hermeswebui_backup_20260810/` → 删除。

## 废弃原因

1. **v0.19.0 起 `hermes dashboard` 本身就是 Web UI**（含 chat/sessions/files/models/logs/cron/skills），`--skip-build` 免 node/npm，一个套件搞定前端+后端，无需独立 WebUI 前端。
2. 独立 HermesWebUI（server.py 前端）是 thin-client，需要连 gateway 内核（HermesCore/远程），架构复杂，且需处理 `agent` 模块缺失、aiohttp、CSRF/iframe 等一堆问题。
3. 自包含 `hermes-agent + hermes dashboard` 更简洁，升级自动跟随。

## 保留的经验（不随废弃删除）

以下是 **Hermes 自包含打包 / fnOS 打包**的通用经验，仍有效，务必保留：

- **自包含 Hermes 打包**：`references/self-contained-hermes-app.md`（python312 venv + pip install hermes-agent + **必须 pip install aiohttp** + API_SERVER_KEY≥16 + config.yaml/.env）。
- **过时点速查**：`references/fnos-dev-guide-outdated-flows.md`（fnos-app-dev-skill 指南中需以实测为准的项）。
- **import 诊断方法论**：`references/fnos-packaging-pitfalls.md` §7（ModuleNotFoundError 诊断、ACL 跨应用授权、cmd/main 正确手动启动——方法论通用）。
- **通用 Hermes 内核打包**：`references/hermes-core-*.md`、`hermes-agent-native-fnos.md`、`gateway-api-server-setup.md`。

## 若未来需要"独立前端"

不推荐再用独立 HermesWebUI。若确实需要自定义 UI，直接用 `hermes dashboard --port 8787`（内置 web UI），或参考 `references/self-contained-hermes-app.md` 的自包含架构。避免回到 thin-client + 独立 server.py 的老路。
