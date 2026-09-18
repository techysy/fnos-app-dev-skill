# fnOS app.tgz 解压位置 & cmd/main 资源路径

## 核心坑：app.tgz 解压无 `target` 层

fnOS 安装 fpk 时，`app.tgz` 直接解压到 `${TRIM_APPDEST}/<子目录>`（即 `/vol4/@appcenter/<App>/<子目录>`），**没有 `target` 中间层**。

**现象**：`cmd/main` 里写 `WEBUI_SRC="${APP_DIR}/target/server"`（只找 target 路径）时，server.py 实际在 `${APP_DIR}/server` → 找不到 → `start` 返回 1 → 应用中心显示 stopped，服务起不来。

**证据对比**（能正常启动的应用）：
- `metacubexd` 的 cmd/main 用**双路径检测**：
  ```bash
  if [ -d "${APP_DIR}/www" ]; then
      WWW_DIR="${APP_DIR}/www"
  elif [ -d "${APP_DIR}/target/www" ]; then
      WWW_DIR="${APP_DIR}/target/www"
  fi
  ```
- `HermesWebUI` 旧版只写 `"${APP_DIR}/target/server"` → 应用中心启动失败

## 正确写法（cmd/main 资源定位模板）

凡用 `${APP_DIR}/target/...` 找资源的，都必须兼容 `${APP_DIR}/...` 双路径：

```bash
APP_DIR="${TRIM_APPDEST:-/var/apps/${APP_NAME}}"
if [ -d "${APP_DIR}/server" ]; then
    WEBUI_SRC="${APP_DIR}/server"
elif [ -d "${APP_DIR}/target/server" ]; then
    WEBUI_SRC="${APP_DIR}/target/server"
else
    WEBUI_SRC="${APP_DIR}/target/server"
fi
```

## 诊断方法

- 看已安装应用的解压位置：`ls -ld /vol4/@appcenter/<App>/<subdir>`（参考能运行的 metacubexd：`www/` 直接在 appcenter 根）
- 进程 cwd 会显示实际路径：`ls -l /proc/<pid>/cwd`（注意重装后可能标记 `(deleted)`）

## 相关

- `app/ui/config 顶层 key 必须 .url`（否则图标消失）——同属 fnOS 打包的隐性约束
- HermesCore 多进程管理方法论见 `references/fnos-packaging-pitfalls.md` §7
