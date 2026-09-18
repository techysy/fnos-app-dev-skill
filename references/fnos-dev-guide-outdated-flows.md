# fnOS 开发指南仓库（fnos-app-dev-skill）过时点速查

来源：`github.com/techysy/fnos-app-dev-skill`（Hermes 私有 skill 仓库），2026-08 审查。做 fnOS 打包时若参考该指南，以下点需**以实测为准**，不要照抄。

> ⚠️ **HermesWebUI 独立套件已废弃（2026-08-10）**：本文件第一部分提到的 `hermes-webui-fnos-package.md`、`hermes-webui-fnos-standalone-repo.md` 等 HermesWebUI 特有 reference 引导的是已废弃的 thin-client 打包，**不要照它打包**。改用自包含 `hermes-agent + hermes dashboard`。**但下面这些通用 fnOS 打包坑（DATA_DIR、aiohttp、appcenter-cli、status return 1）仍有效**，对任何 Python venv 应用都适用。完整废弃说明见 `hermes-webui-deprecated.md`。

## 一、Hermes 相关文档过时

| 文件 | 过时点 |
|------|--------|
| `references/hermes-webui-fnos-package.md` L136 | cmd/main 模板 `DATA_DIR="${TRIM_PKGVAR:-${APP_DIR}/var}"` 是**错误写法**。1.1.31xx 下 `${APP_DIR}/var` 指向只读安装目录，服务起不来。应为 `/vol4/@appdata/<App>`。且模板仍是"连远程 gateway"模式，未反映自包含 |
| `references/hermes-agent-native-fnos.md` / `gateway-api-server-setup.md` | 把 gateway 启动的 `aiohttp not installed` 标注为 false positive —— **错的**。aiohttp 必须装，否则 API server 起不来 |
| `references/hermes-webui-fnos-standalone-repo.md` L67-70 | 要求"版本号与上游同步" —— **过时**。techysy 已用独立版本号（1.0.1/2.0.0），不再同步 upstream tag |

## 二、SKILL.md 内部矛盾

| 矛盾点 | 出处 A | 出处 B |
|--------|--------|--------|
| `.01` 版本后缀 | L175「do NOT append `.01`」 | L184 发布示例 `gh release create v0.5.45.01` |
| `DATA_DIR` 默认值 | L415 警告别用 `${APP_DIR}/var` | L728 例子里又用了 `${APP_DIR}/var` |
| 版本号策略 | L175 要求"沿用上游版本号" | 实际 techysy 已独立版本号 |

## 三、appcenter-cli 说明过时
- `install-fpk` / `install-local` 在 fnOS 1.1.31xx 已移除，只能 App Center Web UI 手动安装。SKILL.md L474-486 已标 deprecated，但 L904-910 仍有误导性描述。

## 四、已更新的部分（确认正确，无需改）
- 交付目录：`/vol1/1000/fnOS App/fpk/<app>/`（新）+ `old_fpk/<app>/`（历史）。**注意是 vol1 不是 vol4**。复制后 `chmod 644`（mode-000 对 App Center 手动安装不可见）。
- `install_dep_apps` 声明运行时依赖（python312/nodejs_v24/go-1.26）有效。
- `status()` 停止时必须 `return 1`，否则 fnOS 从不调 start。
- 进程必须用 App Center 启动（app 用户），别用 SSH 手动 start。

## 使用原则
参考该指南时，凡涉及 cmd/main 模板、aiohttp 依赖、版本号策略、appcenter-cli，**一律以本技能 + 实测为准**。
