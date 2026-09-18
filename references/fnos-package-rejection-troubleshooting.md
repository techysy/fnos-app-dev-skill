# fnOS "应用包不符合系统要求" 排查清单

App Center 安装 fpk 报「应用包不符合系统要求」时，`fnpack build` 往往能成功（fnpack 的校验宽松，App Center 安装校验更严）。按顺序排查：

## 1. manifest 空字段（高发）
不要写**空值字段**，如 `install_dep_apps =`（没有依赖就整行删掉）。空字段导致 manifest 解析失败。
```ini
# ✗ 错
install_dep_apps      =
# ✓ 对：零依赖应用整行删除；有依赖才写
install_dep_apps      = nodejs_v24
```

## 2. desktop_applaunchname 必须保留 appname 连字符（高发，2026-08 Hugo 案例）
`desktop_applaunchname` 必须 = `<appname>.Application`，**连字符要保留**。
```ini
appname               = hugo-blog
desktop_applaunchname = hugo-blog.Application   # ✓ 保留连字符
# ✗ hugoblog.Application 去掉连字符 → 被拒
```
对照可安装应用：`fygo-browser` 的 applaunchname 是 `fygo-browser.Application`（保留连字符）。`app/ui/config` 的 key 也要同步一致。

## 3. service_port 必须是高端口（2026-08 Hugo 案例）
`service_port = 1313` 太低被拒。已安装应用端口都 ≥5000（20127/20128/8005/20365/5122）。
```ini
service_port = 13133   # 用高端口，保留语义（1313 → 13133）
```
manifest、cmd/main（`PORT="${TRIM_SERVICE_PORT:-13133}"`）、app/ui/config 的 port 三处同步。

## 4. ICON 必须是 RGBA（2026-08 Hugo 案例）
ICON.PNG / ICON_256.PNG 需带 alpha 通道（RGBA），RGB 可能被拒。对比可装的 strava 图标是 RGBA。
```bash
file ICON.PNG   # 应为 "8-bit/color RGBA, non-interlaced"
# PIL 生成时用 Image.new('RGBA', ...)，不要用 'RGB'
```

## 5. config/resource JSON 格式严格（2026-08 Hugo 案例）
fnOS 严格校验 resource 的缩进/换行。`"shares": [` 的 `[` 必须同行；`"rw": [...]` 同行。对照可装的 strava。
```json
{
    "data-share":
    {
        "shares": [
            {
                "name": "myapp",
                "permission":
                {
                    "rw": ["myapp"]
                }
            },
            {
                "name": "myapp/data",
                "permission":
                {
                    "rw": ["myapp"]
                }
            }
        ]
    }
}
```
config/privilege 也需 4-space 缩进（`"run-as": "package"`）。

## 6. 其它
- app/www 目录勿为空（补一个占位 index.html）
- 生命周期脚本（cmd/）9 个尽量齐全
- `desktop_uidir = ui`、`desktop_applaunchname` 与 ui/config key 匹配
- 对照法：解包一个**已知可安装**的应用 fpk 和你的 fpk，`diff` manifest/config/cmd 结构，差异即线索

## 7. 拿到精确报错
- SSH 用户无 root，`appcenter-cli`（root 700 权限）不可用
- 需要 root 才能精确安装报错 → 请用户提供 sudo 密码，或让用户在 App Center 操作
- 安装日志可能在 `/var/log/syslog`、`/var/log/user.log`（通常查不到具体原因，靠对照 diff）

## 8. @appdata vs @appshare
- `@appdata/<App>/` = 标准数据目录；`@appshare/<App>/` = 应用共享目录（应用默认 700 可写）
- 两者应用都有权限；默认用 `@appdata`，用户要求可改用 `@appshare`
