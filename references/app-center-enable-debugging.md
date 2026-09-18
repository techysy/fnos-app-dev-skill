# 排障：App Center 应用「无法启用」+ cmd/main 运行诊断

排查 `hugo-blog` fnOS 应用「App Center 无法启用」时沉淀的方法，适用于任何用 `cmd/main` 做启停的 fnOS 应用。

## 关键事实：cmd/main 的调用上下文

- **App Center 以应用用户（如 `hugo-blog`，非 SSH 用户）调用 `/var/apps/<app>/cmd/main start|stop|status`。**
- `cmd/main` 脚本**本身不切换用户**——它依赖 App Center 以正确用户调用。SSH 手动调用会以当前 SSH 用户（如 `<user>`）启动 hugo/manager 进程，导致数据目录属主错误、权限失败。
  - **规范：启停走 App Center，勿用 SSH 用户手动起应用服务。**
- 安装后的实际结构（旧式布局）：
  - `/var/apps/<app>/cmd/main` — 真正的启停脚本（跟源码 `cmd/main` 一致）
  - `target -> /vol4/@appcenter/<app>`（server/ui/www 实际内容）
  - `var -> /vol4/@appdata/<app>`（数据目录，含 blog/、api_token、*.log、*.pid）
  - 对比：官方/新式应用跑在 `/usr/local/apps/@appcenter/<app>` 下自带 server 进程。

## 诊断「无法启用」的正确顺序

1. **先确认 App Center 到底调用了什么**：看数据目录的 `hugo-diag.log`（cmd/main 每次调用都会写 `=== date call: '<cmd>' USER=<u> ===`，含 TRIM_APPDEST/TRIM_PKGVAR/DATA_DIR/port）。
   - 能确认：App Center 是否以正确用户（hugo-blog）调用了 `start`。
2. **看应用自己的运行日志**：`hugo.log`（hugo server 渲染/启动输出）、`manager.log`（管理面板 API 请求）。
   - **渲染失败会伪装成「无法启用」**：hugo server 进程可能起来了但渲染报错，最终端口没监听 → App Center 判失败。
3. **看端口**：`ss -tlnp | grep <port>`（如 13133 博客 / 13134 管理面板）。
4. **验证已运行状态**：`cmd/main status` 或直接 curl 端口（HTTP 200）。

## 典型根因：SCSS 主题需 Dart Sass

- 若 `hugo.log` 报 `TOCSS-DART: ... You need to install Dart Sass ... this feature is not available in your current Hugo version`，根因是**当前主题是 SCSS 主题**（如 `anatole-master`），而系统没装 Dart Sass → 渲染失败 → 应用无法启用。
- **临时恢复**：把 `config/_default/config.toml` 的 `theme = "..."` 切到无 SCSS 主题（如 `minimal`），并备份原配置（`cp config.toml config.toml.bak`）。改完回 App Center 重新启用。
- **健壮性方向**：正式发布前考虑装 Dart Sass 并在应用里支持，否则用户一换 SCSS 主题就崩。
- 注意数据目录 `config/_default/config.toml` 属主是 `hugo-blog`（权限 700），但 SSH 用户若属 `Administrators` 组通常仍可写。

## cmd/main `status` 误报「stopped」的坑

- `cmd/main start` 用 `setsid <bin> ... &` 后台化后再 `echo $! > pidfile`。**`setsid` 可能 fork 出子进程，`$!` 记录的不是实际存活进程 PID** → 之后 `cmd/main status` 检查 pidfile 里的 PID 已死 → 误报 `stopped`，尽管应用实际在跑、端口在监听。
- **判据用端口监听而非 pid 文件**：`ss -tln | grep :<port>`；App Center 自身判断运行状态走 systemd/端口，不受此影响。
- 这属于应用可改进点（start 应记录真实 PID），排障时不要被 `status` 的 stopped 误导。

## 同名手动 systemd 服务干扰判断

- 若 `/etc/systemd/system/<app>.service` 被手动创建过（如跑另一个目录/端口），它占用服务名，会让「App Center 是否在管这个应用」变得混乱。判断标准：service 文件创建时间 vs 应用安装时间（App Center 安装的应用 service 应与其同时生成）；手动服务往往指向非 @appdata 的 source（如 `/opt/...`）。
- 手动服务与应用（cmd/main 管理的 13133 等端口）是两套独立进程，通常不冲突；但会干扰「哪个是 App Center 应用」的判断。
