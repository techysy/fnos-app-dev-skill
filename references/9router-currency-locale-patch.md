# 给编译后 Next.js bundle 打补丁：货币/成本显示按界面语言切换

适用于 9Router 这类打包成 standalone 的 Next.js 应用——改已安装 bundle（不是源码）来改变前端行为。

## 背景
9Router usage 页成本硬编码美元。需求：中文界面显示人民币 ¥，英文保持 $。

## 关键事实
- 定价数据在 `open-sse/providers/pricing.js`，单位 **USD per million tokens**
- `calculateCostFromTokens()` 算出美元成本
- 前端多处硬编码 `$`，编译后集中在 **一个 chunk**：`static/chunks/5497-ec8d04fe35d82d0b.js`（4 处 `\`$${...toFixed(...)}\``）
  - 预估成本 `(t=e.totalCost,\`$${(t||0).toFixed(2)}\`)`
  - 概览卡片 formatter `p=e=>\`$${(e||0).toFixed(2)}\``
  - 图表 formatter `F=e=>\`$${(e||0).toFixed(4)}\``
  - Cost/call `format:e=>0===e?"Free":\`$${e.toFixed(4)}\``
- i18n locale 存在 cookie：`locale=zh-CN` / `locale=en`（`src/i18n/config.js` `LOCALE_COOKIE="locale"`）

## 补丁步骤
1. 注入 helper 到 chunk 顶部（`"use strict";` 之后）：
   ```js
   function __c$(n,p){var d=(document.cookie.match(/locale=([^;]+)/)||[])[1]||"";return /zh/i.test(d)?("¥"+((n||0)*7.2).toFixed(p||2)):("$"+((n||0).toFixed(p||2)))};
   ```
   - `zh` 正则匹配 zh-CN/zh-TW；`¥` 用字面 UTF-8；汇率硬编码 7.2
2. 替换 4 处成本表达式为 `__c$(...)` 调用（见 scripts/patch_currency.py）

## 验证
```bash
# helper 逻辑实测
node -e "function __c\$(n,p){...}; global.document={cookie:'locale=zh-CN'}; console.log(__c\$(0.2));"  # → ¥1.44
# 整个 chunk 语法
node --check <chunk>.js   # 必须"语法 OK"
# 服务器在提供补丁后 bundle
curl -s "http://127.0.0.1:20128/_next/static/chunks/5497-ec8d04fe35d82d0b.js" | grep -c "__c\$"
```

## 陷阱
- 备份：`<chunk>.currency.bak.<ts>`
- 硬刷新浏览器生效（chunk hash 不变，浏览器缓存旧 JS）
- 改的是构建产物，**升级/重装 fpk 会丢**
- **只改已安装实例**——要烘焙进 fpk 需对 fpk 内 `app/server` 的 bundle 同样打补丁

## 复现脚本
`scripts/patch_currency.py` — 完整可复用补丁（注入 helper + 4 处替换，幂等，自动备份）。
用法：scp 到 NAS 后 `python3 patch_currency.py`。
