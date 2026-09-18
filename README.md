# 🐂 fnOS App Development Skill

[![fnOS 1.1.31xx](https://img.shields.io/badge/fnOS-1.1.31xx+-orange.svg)](https://developer.fnnas.com/docs/guide)
[![fnpack](https://img.shields.io/badge/build-fnpack-blue.svg)](https://developer.fnnas.com/docs/guide)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 🏔️ 飞牛 NAS (fnOS) 应用开发完整踩坑记录 — AI Agent 可加载的 dev skill

包含从零到发布的全流程经验：manifest 格式、生命周期脚本、TRIM_APPDEST 路径差异、fpk 安装被拒根因、Next.js standalone 打包、静态文件打包、Node 原生模块（glibc/多架构）、fnpack 构建验证、统一网关、多版本/多架构交付、零依赖 Python 管理面板、SSH 后台进程清理等。

文中示例 IP / 用户名 / 密钥均为占位符（`<NAS_IP>`、`<user>`、`<YOUR_API_KEY>`），替换成你的环境即可用。

## 🌐 用这套方法打包出的开源产出

| 项目 | 说明 | Release |
|---|---|---|
| [10router](https://github.com/techysy/10router) | 🚀 AI 路由器（fnOS fpk / Docker / npm 桌面版） | [v1.1.2](https://github.com/techysy/10router/releases) |
| [deepseek-harness-fnos](https://github.com/techysy/deepseek-harness-fnos) | 🐳 DeepSeek Harness (dsh) agent 浏览器 UI，支持 x86/ARM 离线包 | [releases](https://github.com/techysy/deepseek-harness-fnos/releases) |
| [mimocode-fnos](https://github.com/techysy/mimocode-fnos) | 🖥️ 小米 MiMo Code 官方 TUI 的 fnOS 打包 | [v0.1.14](https://github.com/techysy/mimocode-fnos/releases) |
| [mihomo-core-fnos](https://github.com/techysy/mihomo-core-fnos) | 🌐 mihomo 内核 + 状态页 fnOS 应用 | [releases](https://github.com/techysy/mihomo-core-fnos/releases) |
| [hugo-blog-fnos](https://github.com/techysy/hugo-blog-fnos) | 📝 Hugo 静态博客 fnOS 应用 | [v0.1.4.14](https://github.com/techysy/hugo-blog-fnos/releases) |
| [strava-panel-fnos](https://github.com/techysy/strava-panel-fnos) | 🚴 Strava 骑行数据面板 | [v1.2.0](https://github.com/techysy/strava-panel-fnos/releases) |
| [metacubexd-fnos](https://github.com/techysy/metacubexd-fnos) | 📊 MetaCubeXD Mihomo 面板 | [v1.270.6](https://github.com/techysy/metacubexd-fnos/releases) |

## 📁 文件结构

```
├── SKILL.md                              # 📖 主文档（完整指南，可被 agent 直接加载）
├── references/                           # 📚 专题踩坑记录（按主题分组，独立成篇）
│   ├── fnos-package-rejection-troubleshooting.md  # 🚫 「应用包不符合系统要求」全根因
│   ├── fnos-packaging-pitfalls.md        # 📦 打包通用坑 + venv 应用排障方法论
│   ├── versioned-release-workflow.md     # 🏷️ 版本化发版/重新打包流程
│   ├── fnos-delivery-and-dual-version.md # 📦 交付目录规范 + url/iframe 双版本
│   ├── fnos-lifecycle-scripts-required.md# 🔧 必需的生命周期脚本
│   ├── fnos-settings-config-pattern.md   # ⚙️ 应用设置模式
│   ├── zero-dep-python-backend.md        # 🐍 零依赖 Python 管理后端
│   ├── nextjs-standalone-bundling.md     # ⚡ Next.js standalone 打包
│   ├── static-file-fnos-app.md           # 📦 静态文件打包模式
│   ├── hugo-static-app-fnos.md           # 📝 Hugo/静态站封装全记录
│   ├── dsh-arm-offline-build.md          # 🐳 ARM 多架构离线打包（manylinux + GitHub Actions）
│   ├── fnos-unified-gateway-microapp.md  # 🌐 fnOS 官方统一网关
│   └── ...（其余见 references/ 目录，按需查阅）
├── scripts/                              # 🛠️ 辅助脚本
│   ├── gen_hollow_hub_icon.py            #    RGBA 图标生成
│   └── patch_currency.py                 #    9router 货币本地化补丁
└── README.md
```

## 🛠️ 核心踩坑速查

| 踩坑 | 症状 | 修复 |
|---|---|---|
| 🔴 TRIM_APPDEST 差异 | "无法启用 / 本地应用启动失败" | cmd/main 双路径检测 |
| 🔴 `.next-cli-build` 隐藏目录 | "Could not find a production build" | `cp -r app/. app/server/` |
| 🔴 fpk mode 000 | App Center 看不到文件 | `chmod 644` 修复 |
| 🔴 service_port 低端口 | 「应用包不符合系统要求」 | 用 ≥5000 高端口（三处同步） |
| 🔴 desktop_applaunchname 去连字符 | 安装被拒 | `<appname>.Application` 保留连字符 |
| 🔴 ICON 非 RGBA / resource JSON `[` 换行 | 安装被拒 | `Image.new('RGBA')`；括号同行 |
| 🔴 manifest 空字段 `install_dep_apps =` | 安装被拒 | 零依赖直接删该行 |
| 🟡 SSH 后台进程残留 | 端口被占用 / 属主污染 | `ssh host 'kill <pid>'` + chown 回应用用户 |
| 🟡 TRIM_PKGVAR 覆盖 DATA_DIR 默认值 | 数据目录落错位置 | 想固定 @appshare 就硬编码，勿用 `${TRIM_PKGVAR:-…}` |
| 🟡 node-forge 缺失 | MITM 证书生成失败 | 从 Dockerfile 补依赖 |
| 🟢 install_dep_apps 依赖声明 | 早期记录"1.1.31xx 拒绝"为过时经验 | 正确做法：`install_dep_apps=nodejs_v24` 自动装运行时（2026-08-08 实测有效） |
| 🔴 Native 模块 GLIBC 不兼容 | `GLIBC_2.42 not found` / native 模块加载失败 | 在 NAS glibc 环境编译，或 manylinux 容器（见 `dsh-arm-offline-build.md`） |
| 🔴 ARM 离线包 | ARM NAS 离线安装 | GitHub Actions `ubuntu-24.04-arm` + `manylinux_2_28_aarch64` 编译（glibc≤2.28） |
| 🔴 多架构 fpk 命名 | 用户选错包 | 规范 `<app>-<ver>[-iframe]-<arch>.fpk`（arch ∈ x86/arm/all） |

## 🤝 用法

- **给 AI agent**：把本仓库放进 agent 的 skills 目录（如 Hermes 的 `~/.hermes/skills/`、Claude Code 的插件目录），agent 在打包 fnOS 应用时会自动加载 `SKILL.md` 并按需翻 `references/`。
- **给人**：直接读 `SKILL.md`（主流程）+ 按症状翻 `references/`（专题细节）。

## License

MIT

---

> 📅 最后更新：2026-09-18 · [developer.fnnas.com](https://developer.fnnas.com/docs/guide)
