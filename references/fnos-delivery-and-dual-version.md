# fnOS 交付目录规范 + 双版本（url/iframe）打包

## 一、交付目录规范

用户要求的交付目录流程（注意 **vol1 不是 vol4**）：

| 版本类型 | 路径 |
|---------|------|
| **新版本** | `/vol1/1000/fnOS App/fpk/<appname>/` |
| **历史版本** | `/vol1/1000/fnOS App/old_fpk/<appname>/` |

要点：
- 每个 app 一个子目录，`fpk/<appname>/` 放当前发布版，`old_fpk/<appname>/` 放历史归档。
- fpk 复制到该目录后 `chmod 644`（mode-000 / 缺读权限的文件，App Center 手动安装看不到）。
- 旧的 `/vol4/1000/SSD/` 交付习惯已废弃，勿再使用。
- 发版时：新版本进 `fpk/<appname>/`，旧版本（若同目录已有）移到 `old_fpk/<appname>/`。
- `.gitignore` 排除 `*.fpk`，fpk 只在 GitHub Release + 本地交付目录。

## 二、双版本打包：url（新标签页）+ iframe（桌面窗口）

fnOS 应用常同时交付两个变体：`type:"url"`（新标签页，全屏）+ `type:"iframe"`（fnOS 桌面窗口内嵌）。

### 自动化打包脚本

```bash
#!/bin/bash
# build-dual.sh — 在 fnOS 构建目录执行
set -e
APP=$(basename "$(pwd)")
VER=$(grep '^version' manifest | awk '{print $3}')

# iframe 版
python3 -c "
import json
p='app/ui/config'
d=json.load(open(p))
d['.url']['${APP}.Application']['type']='iframe'
json.dump(d,open(p,'w'),ensure_ascii=False,indent=2)
"
fnpack build && mv ${APP}.fpk ${APP}-${VER}-iframe.fpk

# url 版（恢复默认）
python3 -c "
import json
p='app/ui/config'
d=json.load(open(p))
d['.url']['${APP}.Application']['type']='url'
json.dump(d,open(p,'w'),ensure_ascii=False,indent=2)
"
fnpack build && mv ${APP}.fpk ${APP}-${VER}.fpk

echo "✅ 双版本打包完成: ${APP}-${VER}.fpk + ${APP}-${VER}-iframe.fpk"
```

### 手动构建流程

1. 先构建 url 版：`app/ui/config` 里 `"type": "url"` → `fnpack build` → `cp myapp.fpk myapp-x.x.x.fpk`
2. 再构建 iframe 版：
   - 复制一份构建目录（**别污染 url 版**）
   - 把 `app/ui/config` 的 `"type": "url"` 改成 `"type": "iframe"`（键名 `.url` 保持不变，只改 type 值）
   - **给 server 源码打 iframe 补丁**：去掉 X-Frame-Options 限制，否则 fnOS 桌面窗口内嵌会白屏/跨域
   - `fnpack build` → `cp myapp.fpk myapp-x.x.x-iframe.fpk`
3. url 版**必须保留安全头**（`frame-ancestors 'none'` + `X-Frame-Options: DENY`），iframe 版才放宽。

**Source repo convention:** `app/ui/config` 保持 `type: "url"`（默认）。iframe 版只在打包时临时切换，不入库。

**Why two versions:** Some users prefer desktop windowed mode (iframe) for quick access alongside others; others prefer full-screen (url) for immersive use. iframe may have CORS issues; url always works but requires tab switching.

### 坑：iframe 版对登录型应用会坏（SameSite cookie）

`type:"iframe"` 对**有自己登录**的应用（密码、session cookie）会失败：跨域 iframe 里浏览器拒绝持久化 `SameSite=lax` 的 cookie → 登录反复跳回登录页/白屏。
- 症状：输对密码却一直跳回登录页；直接浏览器开 `http://<nas>:<port>` 却正常（非跨域 iframe）。
- 判断：`curl -s -X POST http://127.0.0.1:<port>/api/auth/login -d '{...}' -D - | grep -i set-cookie`，看到 `SameSite=lax` 即中招。
- 修复：登录型应用只发 `type:"url"` 版。别靠改 `SameSite=None`（会强制 `Secure`，需要 HTTPS，fnOS 纯 HTTP 没有）。

> ⚠️ **Note (2026-08, 9Router): even `type:"url"` does NOT help on the 飞牛 mobile App** — the fnOS mobile App opens EVERY app via its own WebView iframe regardless of url/iframe type. For an internal-only login app, the pragmatic fix is to disable the app's login in its own DB/config.

### 坑：url 版勿从已打 iframe 补丁的 server 源码构建

若 server 源码来源是「已装 iframe 版」（helpers.py 已 `frame-ancestors *` + `SAMEORIGIN`），直接拿来做 url 版会**误带 iframe 补丁**。url 版需反向恢复安全头再打包。构建前先 `grep -n "frame-ancestors\|X-Frame-Options" app/server/api/helpers.py` 确认状态。

## 三、GitHub Release 发布

```bash
gh release create v<ver> <app>-<ver>.fpk <app>-<ver>-iframe.fpk \
  --title "<app> v<ver>" --notes "..."
```

验证资产：
```bash
gh release view v<ver> --json assets --jq '.assets[] | "\(.name): \(.size)"'
# re-upload if missing: gh release upload v<ver> <files...>
```

**Keep the built fpk OUT of git**: the fpk is a build artifact, not source — do NOT commit it to the wrapper repo. Add `*.fpk` to `.gitignore`.

## 四、多架构命名规范

```
<app>-<ver>[-iframe]-<arch>.fpk
```
arch ∈ `{x86, arm, all}`:

| 后缀 | 含义 |
|------|------|
| `-x86` | x86_64 离线（含 x86 原生模块） |
| `-arm` | ARM64 离线（含 ARM64 原生模块, glibc≤2.28 兼容） |
| `-all` | 在线（无原生模块, 装时按架构编译, x86+ARM 通用） |

`-iframe` 在版本号和架构之间：`dsh-0.1.0-rc.6-iframe-x86.fpk`。

## 五、相关

- `references/dsh-arm-offline-build.md`：多架构离线打包（manylinux + GitHub Actions）。
- `references/versioned-release-workflow.md`：版本化发版流程 + 版本号强制检查。
- `references/self-contained-hermes-app.md`：自包含 Hermes 打包。
- SKILL.md 的「Dual-Version fpk」章节也有基础说明。
