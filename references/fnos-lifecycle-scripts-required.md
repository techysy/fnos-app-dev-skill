# fnOS Required Lifecycle Scripts

## Complete List (ALL 9 are mandatory)

fnOS validator rejects fpk if ANY of these are missing — even unused ones must exist as no-op.

```
cmd/main              # start/stop/status/restart — REQUIRED, actual logic
cmd/install_init      # pre-install — usually no-op for bundled source
cmd/install_callback  # post-install — venv creation, deps
cmd/config_init       # pre-config change — no-op
cmd/config_callback   # post-config change — save wizard values
cmd/upgrade_init      # pre-upgrade — no-op
cmd/upgrade_callback  # post-upgrade — no-op
cmd/uninstall_init    # pre-uninstall — stop processes, cleanup
cmd/uninstall_callback # post-uninstall — remove data dirs
```

## No-op Template

```bash
#!/bin/bash
# <script_name> — no-op placeholder
exit 0
```

## Verified Working Structure (v1.3.0 / 2026-07-30)

Source: `/vol4/1000/SSD/old/HermesWebUI-v1.3.0.fpk`

```
myapp/
├── manifest
├── ICON.PNG (64x64)
├── ICON_256.PNG (256x256)
├── app/
│   ├── server/          # Source code (bundled)
│   ├── ui/
│   │   ├── config       # Entry config (type: "url")
│   │   └── images/      # Icons (icon_64/128/256.png)
│   └── www/             # Static files (if any)
├── cmd/                 # ALL 9 scripts present
├── config/
│   ├── privilege        # 4-space indented JSON
│   └── resource         # 4-space indented JSON, 2 shares
└── wizard/              # OPTIONAL but may cause issues
```

## Why This Matters

The fnOS validator checks for script existence BEFORE running them. Missing `config_init` or `upgrade_callback` causes "应用包不符合系统版本要求" — same error as wrong manifest format. This is undocumented in official fnOS docs.

## fnOS Config Directory Formats

### config/privilege (4-space indented)
```json
{
    "defaults":
    {
        "run-as": "package"
    }
}
```

NOT minified: `{"defaults": {"run-as": "package"}}` — causes rejection.

### config/resource (4-space indented, 2 shares minimum)
```json
{
    "data-share":
    {
        "shares":
        [
            {
                "name": "AppName",
                "permission":
                {
                    "rw":
                    [
                        "AppName"
                    ]
                }
            },
            {
                "name": "AppName/data",
                "permission":
                {
                    "rw":
                    [
                        "AppName"
                    ]
                }
            }
        ]
    }
}
```

## Build Requirements

- `fnpack build` requires `app/` directory with actual files — does NOT accept pre-built `app.tgz`
- Extract tarballs into `app/` before building
- **`install_dep_apps` 是 fnOS 官方的运行时依赖声明方式（已实测有效，2026-08-08）**：在 manifest 加 `install_dep_apps=nodejs_v24`，用户在 App Center 安装应用时会**自动安装/启用 nodejs_v24**。9Router v0.5.51 实测：卸载 nodejs_v24 后装最新 fpk，fnOS 自动装回 nodejs_v24（`/var/apps/nodejs_v24/manifest` version 24.15.0-1），应用正常启动（`health ok`、端口监听）。运行时路径用 `/var/apps/nodejs_v24/target/bin/node`（`target` 是指向 `/vol4/@appcenter/nodejs_v24` 的符号链接）。⚠️ 早期曾记录"`install_dep_apps` 导致 fnOS 1.1.31xx+ 拒绝安装"——此为过时/错误经验（可能因格式或旧版本），当前正确做法是声明依赖；若某 fnOS 版本仍拒绝，检查 `install_dep_apps` 格式（KEY=VALUE，等号两侧空格）而非删除它。
- Stripped files before bundling: `CHANGELOG.md tests/ docs/ .github/ .git/` reduces fpk from 22MB to ~4MB
