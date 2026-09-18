# fnOS App 版本化发版/重新打包流程

标准发版流程，适用于所有 fnOS 应用。**每次发版必须按此执行。**

---

## 版本号规则

- 格式：`主.次.修订`（如 `1.0.4`、`1.1.1`）
- 每次较大功能改动升一版
- 上游包装类应用：版本号对齐上游（如 9Router `0.5.45`），不加 `.01` 后缀

### 版本号一致性

应用版本可能出现在多个位置，**发版前必须全部同步**。常见位置：

| 文件 | 位置 | 说明 |
|------|------|------|
| `manifest` | `version = x.x.x` | fnOS App Center 显示版本 |
| `cmd/main` | `APP_VERSION:-x.x.x` | 启动时传递 |
| `app/status_server.py` | `APP_VERSION = "x.x.x"` | 状态页显示（如有） |

> ⚠️ 任一不一致都会导致「App Center 显示新版本，状态页/日志显示旧版本」。

---

## 发版前版本检查（强制）

打包前执行以下脚本，**三处版本号必须一致**才能继续：

```bash
#!/bin/bash
# check-version.sh — 从项目根目录执行
set -e

MANIFEST_VER=$(grep '^version' manifest | awk '{print $3}')

# 检查 cmd/main 中的版本
CMD_VER=$(grep -oP 'APP_VERSION:-\K[^"]+' cmd/main 2>/dev/null || echo "")

# 检查 status_server.py 中的版本（如有）
STATUS_VER=""
if [ -f app/status_server.py ]; then
  STATUS_VER=$(python3 -c "
import re, sys
try:
    m = re.search(r'MIHOMO_APP_VERSION.*?[\"\\'](.+?)[\"\\']', open('app/status_server.py').read())
    print(m.group(1) if m else '')
except: print('')
" 2>/dev/null || echo "")
fi

echo "manifest=$MANIFEST_VER  cmd=$CMD_VER  status=${STATUS_VER:-N/A}"

# 验证一致性
OK=true
if [ -n "$CMD_VER" ] && [ "$CMD_VER" != "$MANIFEST_VER" ]; then
  echo "❌ cmd/main 版本 ($CMD_VER) ≠ manifest ($MANIFEST_VER)"
  OK=false
fi
if [ -n "$STATUS_VER" ] && [ "$STATUS_VER" != "$MANIFEST_VER" ]; then
  echo "❌ status_server.py 版本 ($STATUS_VER) ≠ manifest ($MANIFEST_VER)"
  OK=false
fi

if $OK; then
  echo "✅ 版本号一致: $MANIFEST_VER"
else
  echo "❌ 版本号不一致！请同步后重试"
  exit 1
fi
```

---

## 重新打包标准步骤

源码/打包构建目录：`/vol1/1000/fnOS App/build/<repo>/`。GitHub 仓库 `app/server/` 被 `.gitignore` 排除（standalone bundle 只在本机）。

1. **改运行时配置**：如 `app/server/.env`（会被打进 fpk、装到 `${TRIM_APPDEST}/server/.env`、启动时加载）。改前先 `cmp` 线上与本地，确认只有想改的字段差异。
2. **升版本**：`manifest` 的 `version` 递增；`CHANGELOG.md` 顶部插入新版本条目。
3. **执行版本检查**：`bash check-version.sh` → 必须输出 ✅。
4. **打包**：`fnpack build` → 生成 `<app>.fpk`（文件名不带版本号）。
5. **生成两个变体**（url 版 + iframe 版）：参考 `fnos-delivery-and-dual-version.md`。
6. **验证 fpk**：`tar xzf <fpk> -O manifest | grep ^version`
7. **放置发版目录**：`/vol1/1000/fnOS App/fpk/<App>/`（chmod 644）。旧版本移到 `old_fpk/`。
8. **同步 GitHub**：提交 `manifest`、`CHANGELOG.md`、`README*`，打 tag，push。
9. **用户 Web UI 手动安装**。

## 验证安装生效

- 已安装 manifest：`cat /var/apps/<App>/manifest | grep ^version`
- 服务进程 PID 变化 + `curl -sf http://127.0.0.1:<port>/api/health`

## 关键权限事实

- **`fnpack build` 不需要 root**：普通用户可直接运行。
- **`appcenter-cli` 需要 root**：且 **`appcenter-cli install-fpk` 已在 fnOS 1.1.31xx+ 废弃/移除**。
- **安装/替换唯一官方路径 = App Center Web UI「手动安装」**。不要用命令行安装。

## 同版本覆盖 / 升级决策（精细区分）

fnOS App Center **拒绝安装与已装版本相同的包**。两条出路，按场景选：

- **版本号已递增**（装 0.1.4.6、发 0.1.4.7）→ App Center **直接升级即可**，无需卸载。这是正常路径，给用户下达指令时也这么说——**别条件反射说"卸载重装"**。
- **必须重推同一版本**（修复内容忘了升版本号）→ 只能**先卸载再重装**，或者补一位第四版本号走直接升级。
- ⚠️ 例外：`ctl_stop = true` 的 **service 类应用**（如带守护进程的内核类），App Center「更新」按钮本身极不可靠（`APP_UPDATE_FAILED` + 回滚）——这类应用**一律先卸载再安装新版**（见常见陷阱 #6）。

**测试包节奏**：每次改动递增第四位（`0.1.4.6` → `0.1.4.7`），正式发版时聚合测试改动升第三位（`0.1.5`）。`in-app APP_VERSION`（UI 品牌区 / bootstrap 端点会展示）必须与 `manifest version` 同步——UI 报的版本正好是确认"部署的构建确实生效"的手段。

**卸载的数据安全**：`/vol4/@appdata/<app>/` 在卸载时**默认保留**（实测 hugo-blog 卸载重装后用户数据仍在；应用启动逻辑检测到已有 config 就不重新初始化）。但仍**必须先备份**再动手：
`cp -r /vol4/@appdata/<app> /vol4/@appdata/<app>-backup-$(date +%Y%m%d_%H%M%S)`

## 排查"应用到底跑没跑"：同名手动服务干扰

手工建过的 systemd unit（如手搓一个 `hugo-blog.service` 跑在旧路径旧端口）与 App Center 应用**同名但不是一个东西**：App Center 卸载不会移除它，还会干扰 start/stop 判断。诊断时看**真实应用端口**和 `cmd/main status` 的输出，别看到同名进程/服务就下结论。

## scp 到 NAS build 目录会落错路径

`scp app/server/manager.py user@nas:/tmp/build/` 把文件放在 build 目录**根**，不是它的 `app/server/` 子目录。落地后先挪位再打包，并在 `fnpack build` **前** grep 确认新代码真的在位——否则 fpk 静默打进旧文件：

```bash
scp app/server/manager.py user@nas:/tmp/build/
ssh nas 'cd /tmp/build && [ -f ./manager.py ] && mv -f ./manager.py app/server/manager.py'
ssh nas 'grep -c "<新功能标记>" /tmp/build/app/server/manager.py'   # ≥1 才继续
ssh nas 'cd /tmp/build && tar xzf <app>.fpk -O manifest | grep ^version'  # 打包后再验
```

## 常见陷阱

1. **版本不同步**：manifest / cmd/main / status_server.py 不一致 → 状态页显示旧版本。**必须执行版本检查脚本**
2. **状态页不更新**：只 cp 运行目录但没重启进程 → 旧进程跑旧代码 → 必须卸载重装
3. **wizard/config 格式**：必须是 `[{ "stepTitle": "...", "items": [...] }]`，缺 `stepTitle` 会打包失败
4. **fpk 文件权限**：必须 `chmod 644`，否则 App Center 手动安装不可见
5. **`.env` 占位值是运行时真实生效的**：源码自带的 `.env` 里 `INITIAL_PASSWORD=change-me` 是示例占位，Next 会加载并**覆盖代码 fallback**。若前端默认密码是 `123456` 而 `.env` 写了别的值，就出现不一致。
6. **⚠️ fnOS 升级机制不可靠（service 类应用）**：`ctl_stop = true` 的 service 应用，App Center「更新」按钮极不可靠（`APP_UPDATE_FAILED` + 回滚）。**必须先卸载旧版再安装新版**。调试：`sudo grep -i 'UPDATE_FAILED' /var/log/syslog | grep <app>`。卸载保留数据目录，配置不丢失。
7. **Running process doesn't pick up file changes**：fpk 重新安装后，旧进程仍在跑旧代码。验证：`ps aux | grep <app>` 看启动时间 + `curl http://127.0.0.1:<port>/ | grep '<new>'` 确认新代码生效。
