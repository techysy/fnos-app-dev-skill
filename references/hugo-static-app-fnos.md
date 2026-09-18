# Hugo/静态站 fnOS 应用封装 + 数据目录 + 校验陷阱

封一个纯静态博客（Hugo 等）为 fnOS 应用的完整经验（2026-08，hugo-blog-fnos v0.1.x）。也适用于任何"二进制 + 数据目录"类应用。

## 架构
```
app/server/hugo        # 二进制（零依赖，打包进 fpk）
app/server/manager.py  # 管理后端（纯 Python 标准库 http.server）：写文章/列文章/主题上传切换
app/server/template/   # 博客源模板（config/content/archetypes/themes/minimal）
cmd/main               # 同时启动 hugo server(13133) + manager(13134)
```

## "应用包不符合系统要求" 的 4 个真因（逐一排除）
1. **manifest 空字段**：`install_dep_apps =`（写了空值）→ 删除该行。Hugo 零依赖无需声明。
2. **service_port 太低**：`1313` → 报"不符合系统要求"。**已装应用端口都 ≥5000**（strava 20127、9router 20128、WxBackup 20365、trim.media 8005）。用高端口如 `13133`。
3. **desktop_applaunchname 必须保留 appname 连字符**：`appname=hugo-blog` → `desktop_applaunchname=hugo-blog.Application`（不是 `hugoblog.Application`）。对照可装的 fygo-browser（`appname=fygo-browser` → `desktop_applaunchname=fygo-browser.Application`）。ui/config 的 key 同步。
4. **config/resource JSON 格式**：`"shares": [` 的 `[` 必须**同行**；`"rw": ["app"]` 同行。对照可装 strava。别把 `[` 放下一行。

## TRIM_PKGVAR 覆盖陷阱（关键）
fnOS 调用 cmd/main 时注入 `TRIM_PKGVAR=/vol4/@appdata/<app>`。若 cmd/main 写 `DATA_DIR="${TRIM_PKGVAR:-/vol4/@appshare/${APP_NAME}}"`，**会被覆盖成 @appdata**，而应用数据实际想放 @appshare（文件管理可见）。
**修复**：忽略 TRIM_PKGVAR，硬编码：
```bash
DATA_DIR="/vol4/@appshare/${APP_NAME}"   # 不要用 ${TRIM_PKGVAR:-...}
```
诊断日志 `/vol4/@appshare/<app>/<app>-diag.log` 会打印 TRIM_PKGVAR 与 DATA_DIR 判定，用于确认。

## 启动失败 permission denied（SSH 手动测试残留）
- 症状：`failed to acquire a build lock: open .../.hugo_build.lock: permission denied` 或 `failed to render pages: open .../public/...: permission denied`。
- 根因：SSH（<user> 用户）手动跑 `hugo --buildDrafts` 测试，生成的 `.hugo_build.lock` 和 `public/` 属主是 <user>；App Center 用应用用户（hugo-blog）启动时无法覆盖。
- **修复**：cmd/main 启动前清理：
```bash
rm -f "${BLOG_DIR}/.hugo_build.lock"
rm -rf "${BLOG_DIR}/public"
```
- 手动部署验证：`TRIM_APPDEST=/vol4/@appcenter/<app> TRIM_PKGVAR=/vol4/@appdata/<app> /var/apps/<app>/cmd/main start`（SSH 用户启动，进程属主 <user>，仅用于验证）。

## 暴露 API 给 agent（bootstrap + Bearer 认证模式）
给应用加 REST API 供本地 agent 查询/创建，用零依赖 token 认证（参照 strava 的 bootstrap 模式）：
- token 存数据目录 `<data_dir>/api_token`（权限 600，`secrets.token_hex(16)` 生成，缺失自动生成）。
- `GET /api/bootstrap` **免认证**，返回 `{ "api_token": ... }`（agent / 前端首次获取 token 的入口）。
- 其余 `/api/*` 需 `Authorization: Bearer <token>`，否则 401。用 `_check_auth()` 读 header 比对。
- **前端自动带 token**：JS 里 `apiFetch()` 包装 fetch，启动时 `initToken()` 先调 `/api/bootstrap` 存 token，再对所有 API 请求加 Bearer header。别在页面里硬编码 token。
- README 文档化 agent 用法（curl 示例：先取 token，再带 Bearer 查/建文章）。
- 手写 multipart 解析上传（`body.split(b"--"+boundary)`），不要用 `cgi.FieldStorage`（3.13 移除、且报 "Cannot be converted to bool"）。

## fnOS 发版规则（用户明确）
1. **本地验证 OK 后再发正式包**
2. **测试包用 `当前版本.第四位累加`**（如 0.1.3.1、0.1.3.2…），不要用正式版本号反复打包
3. **测试过程记录更新点/问题点**（TEST_LOG），正式发布时聚合到 CHANGELOG

## 图标
- ICON.PNG/ICON_256.PNG 须 **RGBA**（带 alpha），对照可装应用（strava）。RGB 会被拒。
- 可用项目官方图标（如 Hugo 官方 `docs/static/favicon-*.png`、`android-chrome-256x256.png`）。
- 桌面图标经 API 服务带 ETag 缓存，换图标后强刷页面（Ctrl+Shift+R）；安装后图标生成于 `/vol4/@appcenter/<app>/ui/icon_{64,128,256}.png`。

## 主题兼容性（三类主题 + 实测坑）
- **module 主题**（themes/ 下 go.mod 声明依赖，如 docuapi）：不能扔进 `themes/` 配 `theme=xxx` 了事——hugo 会尝试下载 module 并超时（`context deadline exceeded`）导致卡死、端口不监听。正确做法是 `hugo mod get`（管理面板提供「从 Hugo Module 安装」），需要 go 运行时（`install_dep_apps = go-1.26` 类声明）。
- **SCSS 主题**（如 anatole）：hugo extended **不带 dart-sass**，`hugo server` 报 `TOCSS-DART: you need to install Dart Sass`。注意一次性 `hugo --buildDrafts` 构建可能掩盖此问题、server watch 模式才暴露。
- **front matter 兼容**：历史文章 `categories: jekyll`（字符串）会让多处 `range .Params.categories` 的主题报 `range can't iterate over jekyll`，需批量改为 `categories: [jekyll]`（数组）。
- **document 型主题**（含 `.Site.Data` 强依赖）直接套博客会 500 /「logged 1 error(s)」——主题切换必须**先验证构建再切换，失败自动回滚**，不能盲切。
- **hugo server watch 不会自动重载主题模板**：切换主题后需重启服务进程，或提供「Rebuild」按钮走异步重建。
- 测试轮结束后**必须清理进程残留与属主**（用户硬性要求）：`pkill -f hugo` + `chown -R <app>:<app>` 数据目录，别让 SSH 用户的残留文件卡住 App Center 启动。
