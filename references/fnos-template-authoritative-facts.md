# fnOS 模板权威事实（解决 references 之间的自相矛盾）

> 来源：2026-08 对 fnOS 技能库 references 做一致性审查时，发现多个"已验证可装"模板与拒绝规则/已知事实冲突。以下是**权威正确**的写法，照此为准；凡与其他 reference 冲突处，以此文件为准。

## 权威事实

| # | 事实 | 权威写法 | 违反后果 |
|---|------|---------|---------|
| a | DATA_DIR 必须默认 `/vol4/@appdata/<App>` | `DATA_DIR="${TRIM_PKGVAR:-/vol4/@appdata/${APP_NAME}}"` | 用 `${APP_DIR}/var` 在 fnOS 1.1.31xx 下落在只读安装目录 → 本地应用启动失败 |
| b | `status()` 停止时必须 return 1 | stopped 分支 `echo stopped; return 1`，running 分支 `echo running; return 0` | status 隐式返回 0 → fnOS 误判 running → 从不调 start |
| c | config/privilege 用 4 空格缩进 | `{\n    "defaults":\n    {\n        "run-as": "package"\n    }\n}`，勿 minified | 拒绝 |
| d | config/resource 至少 2 个 share | `AppName` + `AppName/data` 两个 share | 与"至少 2 个"规则不符 |
| e | 进程必须用 App Center 启动（app 用户），别用 SSH 手动启动 | 应用中心图标启动；SSH 手动跑会污染属主/成孤儿进程 | venv/日志/进程属主错 → 应用中心启动失败 |

## 易踩的模板坑（references 里确实存在，别照抄）

1. **config/resource 方括号必须内联**：`"shares": [` 和 `"rw": ["AppName"]` 的 `[` 必须和 key 同行。
   - ⚠️ `fnos-lifecycle-scripts-required.md` 与 `hermes-webui-fnos-package.md` 的 "Verified Working / v0.3.1 verified" 示例把 `[` 换到下一行（`"shares":\n[`）——这与所有拒绝类文档"`[` 换行会被拒"**冲突**。拒绝规则为准，用内联括号。

2. **status() 模板要带 return 1**：任何只 `echo stopped` 不 `return 1` 的 status() 模板都是 bug（即使它旁边标了 CRITICAL 警告）。
   - SKILL.md 曾出现过"模板本身是 bug 写法 + 紧邻 CRITICAL 说明这是 bug"的自相矛盾。照抄模板即踩坑。

3. **DATA_DIR 不要用 `${APP_DIR}/var`**：`hermes-webui-fnos-package.md` 的 cmd/main 主模板曾用 `${APP_DIR}/var`（同文件 uninstall 脚本却用 `/vol4/@appdata`）。以事实 a 为准。

4. **cmd/ 生命周期脚本数量**：不要求严格 9 个全有。实测 strava 只有 7 个（缺 config_init/config_callback）能装。config_init/config_callback/upgrade_* 缺失**不会**导致"应用包不符合系统要求"拒绝；但放齐（no-op `exit 0`）更稳妥。凡是说"缺任一即拒"的都过时。

## 如何决定哪个说法为准

当某 reference 的 "verified/可装" 示例与拒绝规则冲突时：
1. 以**拒绝类文档**（fnos-package-rejection-troubleshooting.md、fnos-packaging-pitfalls.md §4 等）一致声明的格式为准；
2. 以**本文件权威事实表**为准；
3. "verified" 示例可能是旧版本实测，不代表当前 fnOS 校验仍接受。
