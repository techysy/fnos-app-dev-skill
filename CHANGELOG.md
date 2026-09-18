# CHANGELOG

## 2026-09-18 · 🌍 转公开前整理（大版本清理）

- **脱敏**：示例 IP → `<NAS_IP>`、登录用户 → `<user>`、真实 API key（XIAOMI/sk-… 片段）→ `<YOUR_API_KEY>`、本地路径 `/home/<user>/.hermes` → `~/.hermes`。全库扫描无残留。
- **去重 40 个 references**（同一主题曾写过多份笔记，各簇保留最完整主干并合并独有内容）：
  - 「应用包不符合系统要求」×10 → `fnos-package-rejection-troubleshooting.md` 一份
  - hugo 系列 ×9 → `hugo-static-app-fnos.md`（并入主题兼容三大坑、进程属主清理铁律）
  - Python 内嵌 JS 转义 ×5 → `python-format-js-escaping.md` 一份
  - 管理面板 WebUI ×4 → `admin-panel-log-console-and-runtime-binary.md` + `panel-theme-i18n.md`（并入 map(t=>) 遮蔽、innerHTML 覆盖、i18n emoji 叠加三坑）+ `zero-dep-python-backend.md`（并入预设资源后端保护、bootstrap token、multipart 手写解析）
  - 安装校验/manifest 坑 ×4 → `fnos-packaging-pitfalls.md`（并入 venv 应用排障方法论：目录地图 / PYTHONPATH 跨 venv / ACL 授权 / 模拟应用中心 env 启动）
  - 版本规则 ×3 → `versioned-release-workflow.md`（并入同版本 vs +1 升级决策、service 应用例外、卸载数据保留与备份、同名 systemd 干扰、scp 落错路径）
- **补同步 9 个文件**：本地 skill 独有、SKILL.md 一直在引用但仓库从未同步的 references（hermes 内核打包 / manifest 元数据 / python-dependency-app 等）。
- **删除** `_private-repo-sync.md`（私有镜像标记，转公开后无意义）。
- **新增** LICENSE（MIT）。README 重写：去"私有仓库"章节、更新文件计数与目录树、开源产出表补 10router / mimocode-fnos / mihomo-core-fnos、新增「用法」章节。

## 2026-08-16 (同步) · dsh ARM 多架构离线打包
- **新增** `references/dsh-arm-offline-build.md`（ARM 离线包方案：GitHub Actions `ubuntu-24.04-arm` + `manylinux_2_28_aarch64` 容器编译 node_modules，glibc≤2.28 兼容；多架构命名 `[-iframe]-<arch>`）
- **更新** `SKILL.md` Dual-Version 章节（补多架构命名规范，见 `dsh-arm-offline-build.md`）
- 对应本机 Hermes skill `fnos-appdev/fnos-node-native-glibc` 的「核心教训 1b」

## 2026-08-13 (同步) · dsh (DeepSeek Harness) fnOS 打包
- **dsh-fnos 首个版本（v1.0.0）**：
  - **新增** `references/dsh-fnos-packaging.md`（@deepseek-ai/dsh 打包经验：dsh web 只绑 127.0.0.1 + browser-trust fence + 官方统一网关 + proxy 重写 Host 头）
  - 仓库 `techysy/dsh-fnos`（deepseek harness agent 浏览器 UI 打包）

## 2026-08-10 (同步) · HermesCore 终端 + 官方统一网关
- **HermesCore v0.6.0 原生终端 + 飞牛官方统一网关**：
  - **新增** `references/fnos-unified-gateway-microapp.md`（fnOS 官方统一网关机制：gatewayPrefix/gatewaySocket、WebSocket 支持、X-Trim 用户 Header）
  - **新增** `references/hermes-web-terminal-pty.md`（Hermes 内置 Web 终端/PTY 机制：pty_bridge、/api/pty WebSocket、--tui vs hermes chat 的 node 依赖区别）
  - **更新** `references/hermes-core-kernel-fnos.md`（架构加原生终端 + 官方统一网关入口）

## 2026-08-10 (同步)
- **HermesWebUI 独立套件废弃决策**（2026-08-10）：不再发布 HermesWebUI 套件，改用自包含 `hermes-agent + hermes dashboard`（v0.19+ dashboard 即完整 Web UI）。
  - **新增** `references/hermes-webui-deprecated.md`（废弃决策记录：废弃范围、原因、保留经验）
  - **新增** `references/self-contained-hermes-app.md`（自包含 Hermes 打包：python312 venv + pip install hermes-agent + **必须 aiohttp** + API_SERVER_KEY≥16 + config.yaml/.env）
  - **新增** `references/fnos-dev-guide-outdated-flows.md`（fnos-app-dev-skill 指南过时点速查，含废弃提示）
  - **新增** `references/hermes-webui-missing-agent-module.md`（ModuleNotFoundError 诊断 / ACL 跨应用授权 / cmd/main 正确启动，方法论通用）
  - **新增** `references/fnos-delivery-and-dual-version.md`、`references/fnos-template-authoritative-facts.md`
  - **更新** `SKILL.md`（加 HermesWebUI 废弃提示，指引自包含方案）
- **HermesCore 迭代为自包含全能套件（v0.5.0）**：
  - **更新** `references/hermes-core-kernel-fnos.md`（架构改为单套件自包含：内核 Gateway :8642 + 内置 dashboard :9119 默认开启 + 状态页 :8648，替代 HermesWebUI 双包架构）

## 2026-08-09 (同步)
- **同步 hugo-blog 应用开发经验（新增 41 + 更新 1 个 references）** — 本地 `fnos-app-development` 今天更新了 42 个 references：
  - **hugo-blog-fnos 应用**：`hugo-blog-fnos-app.md`、`hugo-blog-admin-panel.md`、`hugo-blog-fnos-debugging.md`、`hugo-blog-fnos-release-workflow.md`、`hugo-blog-fnos-pitfalls.md`、`hugo-blog-fnos-theme-runtime.md`、`hugo-app-pitfalls.md`、`hugo-app-themes-data-dir.md`、`hugo-static-app-fnos.md`
  - **admin panel 模式**：`admin-panel-patterns.md`、`admin-panel-webui-patterns.md`、`admin-panel-log-console-and-runtime-binary.md`、`admin-panel-js-in-python-escaping.md`、`python-manager-embedded-js-escaping.md`、`frontend-in-python-string-js-escaping.md`、`single-file-webui-js-pitfalls.md`、`python-format-js-escaping.md`
  - **fpk 打包/拒绝检查**：`fpk-rejected-format-not-system-requirements.md`、`fpk-rejected-system-requirements-checklist.md`、`fpk-rejection-causes.md`、`fpk-rejection-root-causes.md`、`fnos-package-rejection-troubleshooting.md`、`fnos-install-rejection-check.md`、`fnos-app-rejection-causes.md`、`package-reject-and-appshare.md`、`fnos-packaging-pitfalls.md`、`packaging-pitfalls.md`、`manifest-validation-and-startup-pitfalls.md`、`installation-rejection-checklist.md`、`install-validation-and-startup-pitfalls.md`、`fnos-app-install-startup-pitfalls.md`、`install-rejection-and-data-dir.md`
  - **启动/排障**：`app-center-enable-debugging.md`、`app-enable-failure-debugging.md`、`fnos-app-pitfalls.md`、`fnos-manifest-and-runtime-pitfalls.md`、`fnos-version-reinstall-data-pitfalls.md`、`fnos-versioning-and-upgrade.md`、`versioned-release-workflow.md`
  - **其他**：`9router-repackage-release.md`
  - **更新**：`fnos-integration-pitfalls.md`

## 2026-08-08 (同步)
- **修正 `install_dep_apps` 过时记录（重要）** — 多处（SKILL.md / references/hermes-webui-fnos-package.md / README.md / fnos-lifecycle-scripts-required.md）曾记录"`install_dep_apps` 在 fnOS 1.1.31xx+ 导致 '应用包格式不符合系统版本要求'，需移除"。
  - **实测（9Router v0.5.51）**：`install_dep_apps=nodejs_v24` 是**有效的运行时依赖声明**——用户在 App Center 安装应用时 fnOS **自动安装/启用 nodejs_v24**，应用正常启动（health ok、端口监听）。
  - 已统一修正为正确做法：声明依赖；若某 fnOS 版本仍拒绝，先检查 manifest 格式（KEY=VALUE 等号两侧空格），再退回 `cmd/install_init` 手动处理。
  - 保留 config/privilege 缩进、config/resource shares 等仍然有效的格式经验。

## 2026-08-04 (同步)
- **新增 `hermes-core-status-version-fix.md`** — HermesCore 状态页底部版本号升级不变的完整 debug 过程：
  - 根因：应用版本号硬编码进 status_server.py（0.4.4.x 用 `STATUS_VER` 常量，0.4.5 直接删掉）→ 升级后版本号不更新/消失
  - 修复：动态从已安装 `manifest` 读取（`CORE_CMD` 推导 app 目录 → 读 `version` 行；备选 `/var/apps/...`、`/vol4/@appcenter/...`），升级自动同步
  - 教训：区分「内核版本」（/health）vs「应用包版本」（manifest）；fpk 里 cmd/ 在顶层不在 app.tgz
- SKILL.md 在「集成原生 dashboard 到自定义内核」段补链接
- **fnos-integration-pitfalls.md 新增「scp 到带空格的 NAS 目标路径静默失败」** — scp 到 `/vol1/1000/fnOS App/...` 退出 0 但文件不更新；先 scp 到无空格临时路径再 NAS 上 cp，md5sum 校验

## 2026-08-03 (同步)
- **fnos-integration-pitfalls.md 新增 5 条**：
  1. Python .format() 模板 JS/CSS 花括号转义 + JS 模板字符串/内联onclick坑 + node --check 诊断
  2. 侧边栏导航 + 移动端汉堡（9Router 风格）
  3. 供应商卡片内联配置（替代 prompt 弹窗）
  4. 默认模型逻辑不强制 9Router
  5. fnOS 打包流程（test 包 4 位版本 vs 正式版）

## 2026-08-03 (同步)
- **fnos-integration-pitfalls.md 新增「WebUI iframe: Desktop OK, Mobile WebView Cross-Origin」** — 移动端 WebView 里 127.0.0.1 是手机本身连不上 NAS 内核，属移动端容器限制，桌面端正常则接受

## 2026-08-03 (同步)
- **fnos-integration-pitfalls.md 新增「status() Must Return Non-Zero When Stopped」** — 应用中心从不调用 start 的根因：status() stopped 返回 0 被 fnOS 误判 running。修复 + 诊断方法（diag log 看是否只有 status 调用）。HermesWebUI v0.52.108 案例

## 2026-08-03 (同步)
- **新增 `hermes-dashboard-integration.md`** — Hermes 原生 dashboard 集成到 fnOS 自定义内核的完整经验：
  - `--skip-build` 无需 node/npm，用 venv 自带 web_dist
  - 公开绑定必须认证；Basic Auth 配置在 config.yaml `dashboard.basic_auth`
  - 登录端点 `POST /auth/password-login`（JSON + provider=basic），不是 /api/login
  - cmd/main 多进程管理（gateway + dashboard + status server）
  - 踩坑：config.yaml 无 dashboard 段时 env 不生效；SSH 后台进程挂起用 setsid

## 2026-08-03 (同步)
- **fnos-integration-pitfalls.md 新增 5 个坑**：
  - HTTPS 混合内容：面板经 fnos.net HTTPS 访问连 HTTP 后端被浏览器拦截（MetaCubeXD 案例），url/iframe 版均不解决，需公网 HTTPS 或 fnOS 桌面 Chrome 直开内网
  - ui/config 顶层 key 必须是 `.url`（否则桌面图标消失，即使 type 是 iframe）
  - 配置状态页前端 JS 必须带 Bearer 鉴权头（否则保存报 401）
  - config.yaml 每次启动都应重新生成（否则配置更新不生效）
  - 合并配置入口：应用自带网页配置则移除 fnOS 应用设置页（wizard/config + config_callback 改 no-op）

## 2026-08-01 (同步)
- **SKILL.md 新增 CRITICAL 坑**：`cmd/main status()` 在服务未运行时必须返回非零退出码（1）。fnOS 依赖 status 退出码判断应用是否运行——若 status 在 stopped 时错误返回 0（被 fnOS 误判为 running），fnOS 从不调用 start，服务无法自动启动。这是 metacubexd(正常) vs strava(异常) 的关键差异
- 同步 `zero-dep-python-backend.md`（补充 SO_REUSEADDR 修复：`ThreadingTCPServer.allow_reuse_address = True` 必须在实例化前设置）
- 新增 `_private-repo-sync.md`

## 2026-08-01 (同步)
- **同步本地 skill → 仓库**：补上 Strava Panel 开发经验
- 新增 `zero-dep-python-backend.md`（零依赖 Python http.server 后端 + SQLite 缓存 + agent 透出接口）
- 新增 `panel-theme-i18n.md`（纯 JS 日夜模式 + CN/EN i18n 面板，无构建步骤）
- SKILL.md 补充：app/ui/config 端口与 manifest service_port 必须一致（否则桌面图标指向错误端口）；旧进程占端口导致 `/api/sync` 前端报 `Unexpected token '<'`；高位不常见端口（20xxx）降低被扫描风险

## 2026-08-01 (同步)
- **同步本地 skill → 仓库**：补上本会话新增内容
- 新增 `9router-currency-locale-patch.md`（成本显示按界面语言切货币：中文 ¥×7.2 / 英文 $，bundle 补丁方法）
- 新增 `9router-debugging.md`（Cloudflare 卡片"无连接"=缺 authModes，bundle 热补丁）
- 新增 `9router-fnos-diagnostics.md`（9Router 数据目录/DB 只读诊断）
- 新增 `scripts/patch_currency.py`（货币补丁脚本）+ `scripts/gen_hollow_hub_icon.py`（空心 hub 图标生成）
- **打包版本号规则**：延续上游官方版本号，**不要**加 `.01`/`.02` 打包后缀（用户明确要求）
- **构建输出位置**：`/vol1/1000/fnOS App/`（注意 `vol1` 非 `vol4`），构建树放 `/vol1/1000/fnOS App/build/<repo>/`，成品 fpk 放 `/vol1/1000/fnOS App/`
- **图标圆角对齐 fnOS 规范**：fnOS app 用**小圆角 ~0-5%**（非 iOS squircle ~22%），实测 HermesWebUI 0% / metacubexd 2.3%

## 2026-08-01
- 从 <user>-skills-hub 分离为独立私有仓库
- 新增 static-file-fnos-app.md（MetaCubeXD 打包模式）
- 新增 nextjs-standalone-bundling.md（9Router 打包模式）
- TRIM_APPDEST 双路径兼容（fnOS 1.1.31xx+）
- 踩坑：fpk mode 000、SSH 后台进程残留、.next-cli-build 隐藏目录

## 2026-07-30
- 初始版本：fnOS 应用开发完整指南
- HermesWebUI 打包经验
- fnpack 构建验证流程

## 2026-08-01 (补录)

### 🆕 fnOS 开放 API 更新 (2026-07-31)

**要求**: fnOS ≥1.2.0401 + App ≥1.34.0

新增开放 API 文档，应用可通过前端 JS SDK 和后端 API 接入 fnOS 能力：
- **调用方式**: api-scope 声明、JS SDK 安装初始化、授权跳转回调
- **授权与文件**: 应用共享授权 vs 用户个人授权
- **文件权限**: `trim.file.checkUserACL` — 后端检查读/写/删除权限
- **路径转换**: `trim.file.convertPath` — /vol1/... → 用户可读路径
- **页面路由**: 前端打开文件/文件管理器/应用设置/外部 URL
- **页面交互**: 获取平台配置、设置标题、监听主题/语言变化
- **错误码**: JS SDK + 后端 API 错误码整理

**影响**: 未来 fnOS app 可用 JS SDK 直接调用文件系统，不再依赖 cmd/main 操作文件。
