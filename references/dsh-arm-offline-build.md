# DeepSeek Harness (dsh) ARM 多架构离线打包

> 2026-08 实测：给 ARM fnOS 设备做 **离线** fpk（内置 ARM64 node_modules 免联网）。
> 对应本机 Hermes skill `fnos-node-native-glibc` 的「核心教训 1b」。
> 目标设备示例：R2S（aarch64, Debian 12 / glibc 2.36, 约 1GB 内存）。

## 问题

给 ARM fnOS 设备做离线 fpk，但：

- **低内存设备不能在 NAS 本机编译**：R2S 约 1GB 内存（可用仅 ~425MB），node-pty 编译会 OOM。
- **直接在现代发行版编译，glibc 要求偏高**：目标设备（Debian 12 / glibc 2.36）跑不起来报 `GLIBC_2.3x not found`。

## 方案：GitHub Actions ARM64 runner + manylinux_2_28 容器

在 **GitHub Actions `ubuntu-24.04-arm`（原生 ARM64 runner，免费，无需申请）** 上用
**`quay.io/pypa/manylinux_2_28_aarch64`** 容器编译 node_modules：

- manylinux_2_28 容器内 glibc = **2.28**，在此编译 → 产物 GLIBC 要求 **≤ 2.28 < 2.36**，任何 glibc ≥ 2.28 的环境都能跑。
- 容器内需先装 **Node 24 官方 aarch64 二进制**（Node 官方最低 glibc 正是 2.28，正好匹配），再 `npm install`。
- 真正需现场编译的只有 **node-pty**；sharp 等自带预编译 ARM 二进制（`@img/sharp-linux-arm64`）。

## 关键步骤（`deepseek-harness-fnos/scripts/build-arm-node-modules.sh`）

```bash
# 1. 下载 Node 24 官方 aarch64 二进制
NODE_FULL=v24.19.0
curl -fsSL -o node.tar.xz "https://nodejs.org/dist/${NODE_FULL}/node-${NODE_FULL}-linux-arm64.tar.xz"

# 2. manylinux_2_28_aarch64 容器内:
#    - 解压 node 二进制 → PATH
#    - npm install @deepseek-ai/dsh@^0.1.0-rc.6   (native 模块在此 glibc 2.28 环境编译)

# 3. 校验所有 .node 原生模块的 GLIBC 要求 ≤ 2.28
readelf --version-info <file>.node | sed -n 's/.*GLIBC_\([0-9.]*\).*/\1/p' | sort -V | tail -1
#   任一 > 2.28 则失败, 需处理
```

## 打包（101 x86 打包机, `deepseek-harness-fnos/scripts/package-arm-offline.sh`）

1. 解压 ARM64 node_modules 到 `app/server/node_modules`
2. manifest: `platform = arm`
3. `fnpack build` → 产出两个变体:
   - `dsh-<ver>-arm.fpk`（url 版）
   - `dsh-<ver>-iframe-arm.fpk`（iframe 版）
4. 交付到 `/vol1/1000/fnOS App/fpk/deepseek-harness/`（chmod 644）

## 多架构命名规范

```
<app>-<ver>[-iframe]-<arch>.fpk
```
arch ∈ `{x86, arm, all}`:

| 后缀 | 含义 |
|------|------|
| `-x86` | x86_64 离线（含 x86 node_modules） |
| `-arm` | ARM64 离线（含 ARM64 node_modules, glibc≤2.28 兼容） |
| `-all` | 在线（无 node_modules, 装时按架构编译, x86+ARM 通用） |

`-iframe` 在版本号和架构之间：`dsh-0.1.0-rc.6-iframe-x86.fpk`。

实际 release 4 个资产（dsh v0.1.0-rc.6）:
```
dsh-0.1.0-rc.6-all.fpk
dsh-0.1.0-rc.6-iframe-all.fpk
dsh-0.1.0-rc.6-iframe-x86.fpk
dsh-0.1.0-rc.6-x86.fpk
```

## 验证

- [ ] `readelf` 校验所有 `.node` 的 GLIBC 要求 ≤ 2.28
- [ ] `file <pty.node>` 显示 `aarch64`
- [ ] 目标 ARM 设备（glibc ≥ 2.28）上能正常启动 dsh web

## 相关文件

| 文件 | 说明 |
|------|------|
| `deepseek-harness-fnos/.github/workflows/build-arm-node-modules.yml` | CI 编译 ARM node_modules |
| `deepseek-harness-fnos/scripts/build-arm-node-modules.sh` | manylinux 容器编译 + glibc 校验 |
| `deepseek-harness-fnos/scripts/package-arm-offline.sh` | 101 打包 `-arm.fpk` |
| `deepseek-harness-fnos/docs/arm-build.md` | ARM 打包指南（§11 新增） |
