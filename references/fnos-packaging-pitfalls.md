# fnOS 打包通用坑 (2026-08 实战)

> 白屏/装不上/应用中心启动失败的三大类根因。与 `hermes-agent-kernel-fnos.md` 互补（后者是 Hermes 内核专属）。

## 1. fnpack build 权限坑

**现象**：`fnpack build` 报 `mkdir /tmp/fnpack.*/app/ui: permission denied`。

**根因**：源 `app/` 目录权限被破坏成 `d---------`(700，无读执行位)。fnpack 用保留权限复制，复制出的 `app` 也是 700，内部 `mkdir app/ui` 失败。

**修复**（build 前必须执行）：
```bash
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod 755 cmd/* wizard/*
rm -rf cmd/__pycache__ app/__pycache__ __pycache__   # 防 .pyc 进包
```

**检查**：`ls -ld app app/ui` 必须为 `drwxr-xr-x`。任何 tar/scp/cp 传输都可能改权限。

## 2. 数据目录属主污染

**现象**：应用中心启动应用失败（白屏/端口不监听），但手动 SSH 能跑。

**根因**：手动 SSH 用 `<user>` 起应用进程（而非应用中心/应用用户），污染 `/vol4/@appdata/<App>/venv` 属主为 <user>。应用中心以应用用户运行时无法访问 <user> 所有的 venv → 启动失败。

**修复**：
```bash
chown -R <AppUser>:<AppUser> /vol4/@appdata/<App>/venv \
  /vol4/@appdata/<App>/hermes_home /vol4/@appdata/<App>/state
```

**教训**：**不要手动 SSH 起 fnOS 应用进程**（会污染属主/成孤儿进程）。必须用应用中心启动，或手动起后立即 chown 回应用用户。

## 3. build 目录残留旧配置漏同步

**现象**：重新打包发布新版本，但装出来的行为和旧版一样（如入口还是 iframe）。

**根因**：重新打包时 `scp` 清单漏了 `app/ui/config`（只同步了 cmd/wizard/manifest），build 目录残留旧配置被打包进 fpk。

**教训**：
- `scp` 同步清单必须包含 `app/ui/config`（入口配置）
- build 前确认 build 目录的 `app/ui/config` 的 `type` 正确（url vs iframe）
- 打包后解包验证：`tar xzf X.fpk && tar xzf app.tgz && cat ui/config | grep type`

## 入口 type 白屏对照

| type | 行为 | 适用 |
|------|------|------|
| `"url"` | 新标签页打开，无 iframe 问题 | **推荐** |
| `"iframe"` | fnOS 桌面窗口内嵌（5666 iframe 嵌入应用端口） | 有跨域问题，WebUI 类应用白屏 |

- **手机 fnOS App 用 WebView iframe 打开图标入口**，即使 type 是 url 也可能走 iframe 容器（见 9Router 经验）
- 入口若指向 JSON API（如 `/health`，无 CORS 头）→ `WebKitErrorDomain code=102`（frame load interrupted）白屏
- **入口应指向真正的 HTML 页面**。纯后台服务想有图标入口，就加一个纯 stdlib `http.server` 状态页（独立端口），入口指向它

## 应用中心 vs SSH 手动跑的差异

- 应用中心以**受限应用用户**（nologin）跑 cmd/main：能建 venv、pip install、绑 TCP 端口（strava/metacubexd/9router 均实证），能写自己 `/vol4/@appdata/<App>/`
- SSH 的 <user>（Administrators 组）**无法 kill 应用用户进程**（`kill: Operation not permitted`）；残留进程（stop 后没死透的）只能应用中心或 root 清理
- 遇到"残留进程占端口、start 认为 running 跳过副服务启动"时，让用户在应用中心先停止再启动
- 应用数据目录属主必须是应用用户，否则应用中心启动失败
- **验证 fnOS 真实运行环境**：strava 的 `core-diag.log` 式无条件诊断日志（`id -un`、`TRIM_APPDEST`、`TRIM_PKGVAR`、`PWD`）是看穿"手动能跑应用中心不行"的关键

## 4. 「应用包不符合系统要求」根因（fpk 已 build 成功但安装被拒）

逐项核对（Hugo Blog 实战，2026-08-09，按概率排序）：

1. **`desktop_applaunchname` 必须完全等于 `<appname>.Application`（保留连字符）**
   - `appname = hugo-blog` → `desktop_applaunchname = hugo-blog.Application`
   - ❌ 去连字符 `hugoblog.Application` 被拒。对照 fnOS 自带 `fygo-browser` 保留连字符。
2. **`service_port` 必须是高端口（实测 ≥5000）**：strava 20127、9router 20128、WxBackup 20365、trim.media 8005。❌ `1313`（Hugo 默认）被拒，改 `13133` 通过。
3. **`config/resource` JSON 括号格式与可装应用一致**：✅ `"shares": [`（`[` 同行）、`"rw": ["app"]` 同行；❌ `[` 换到下一行被拒。
4. **ICON.PNG / ICON_256.PNG 必须 RGBA**（PIL `Image.new('RGBA',...)`），RGB 被拒。
5. **manifest 不留空字段**（如空 `install_dep_apps =`）→ 解析失败被拒。零依赖应用直接删该行。

## 5. fnOS 注入 TRIM_PKGVAR 覆盖数据目录默认值

`DATA_DIR="${TRIM_PKGVAR:-/vol4/@appshare/<app>}"` **会被 fnOS 注入的 `TRIM_PKGVAR=/vol4/@appdata/<app>` 覆盖**，实际落到 @appdata。
- 要让博客源统一在 `@appshare`（文件管理可见、可管理），**硬编码忽略 TRIM_PKGVAR**：
  ```bash
  DATA_DIR="/vol4/@appshare/${APP_NAME}"
  ```
- 诊断看 `<app>-diag.log` 的 `TRIM_PKGVAR=` / `DATA_DIR=` 实际值。

## 6. `.hugo_build.lock` 属主阻塞启动

- SSH（个人用户）手动跑 `hugo server --buildDrafts` 会生成 `.hugo_build.lock`，属主 SSH 用户。
- 应用中心用应用用户启动时无法写该 lock → `failed to acquire a build lock ... permission denied` → App Center 报「本地应用启动失败」。
- 修复：`rm -f <blog>/.hugo_build.lock` + `chown -R <appuser>:<appuser> <blog>`；**cmd/main 在启动 hugo 前 `rm -f "${BLOG_DIR}/.hugo_build.lock"`**（最健壮）。
- 教训：SSH 手动测试服务后，残留进程/文件属主是 SSH 用户，应用用户无法接管；测试后清理进程（`pkill -f "hugo server"`）和 lock。

## 7. fnOS 应用目录架构与通用排障机制（任何 venv 类应用适用）

**目录地图**：
```
/var/apps/<App>/                 # 应用根 (TRIM_APPDEST)
├── cmd/main                     # 生命周期脚本 (start/stop/status/restart)
├── var -> /vol4/@appdata/<App>  # 软链，DATA_DIR (TRIM_PKGVAR)
├── target -> /vol4/@appcenter/<App>   # 软链，应用本体
├── etc -> /vol4/@appconf/<App>
└── home -> /vol4/@apphome/<App>
```
进程以**应用专属 nologin 用户**运行（`ps aux` 第一列即判定"App Center 起的还是你手动起的"）。

**ModuleNotFoundError / 某 API 500 ≠ 权限问题**：先 grep 应用日志的 `Traceback|ModuleNotFoundError` 定位缺哪个 import，再决定修哪个 venv。双包场景（前端 venv 惰性 import 后端模块）下，部分 API 200、部分 500 是正常表现——别被"工作区 API 是 200"误导，按**具体报错功能**定位。

**跨 venv 复用模块（治标）**：`cmd/main` 启动前 `export PYTHONPATH="$PYTHONPATH:<另一个应用 venv>/lib/python3.12/site-packages"`——必须指整个 site-packages 目录，软链单个模块会连锁缺依赖。**治本**是自包含打包（依赖装进自己的 venv），别长期依赖这个 hack。

**跨应用用户授权用 ACL 不改属主**：
```bash
setfacl -R -m u:<AppUser>:rwx /vol4/@appdata/<OtherApp>
setfacl -R -d -m u:<AppUser>:rwx /vol4/@appdata/<OtherApp>   # 默认继承，新建文件也授权
```
ACL 只作用到已存在路径，深层 `drwx------` 子目录不会自动继承，需单独授权。验证要实际用目标身份跑 `runuser -u <AppUser> -- <app_python> -c '...'`，别只看 getfacl。

**手动重启 cmd/main 必须模拟应用中心 env**（直接 `sudo cmd/main restart` 会以 root 起 + DATA_DIR 落错）：
```bash
sudo runuser -u <AppUser> -- env \
  TRIM_APPNAME=<App> TRIM_APPDEST=/var/apps/<App> \
  TRIM_PKGVAR=/vol4/@appdata/<App> \
  /var/apps/<App>/cmd/main start
```

## 发版规则（用户明确要求，2026-08-09）

1. **本地验证 OK 后再发正式包**。
2. **测试包用「当前版本.第四位累加」**：`0.1.3.1`、`0.1.3.2`。不要用正式版本号反复打包不同内容。
3. **测试过程记录更新点/问题点**（如 `docs/TEST_LOG.md`），正式发布时聚合到 CHANGELOG。
