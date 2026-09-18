#!/usr/bin/env python3
"""给 9Router bundle 打补丁：成本显示按界面语言切换货币。
中文界面(zh-CN/zh-TW)显示 ¥(乘7.2汇率)，英文显示 $。
在 chunk 顶部注入 __c$ helper，替换 4 处成本格式化。
用法：scp 到 NAS 后 python3 patch_currency.py（幂等，自动备份）
"""
import shutil, time, re

CHUNK = "/vol4/@appcenter/9router/server/.next-cli-build/static/chunks/5497-ec8d04fe35d82d0b.js"
# 版本可能升级导致 chunk hash 变化——升级后先 grep 定位：
#   grep -rl '`\$\${(t||0).toFixed(2)}`' <build>/static/chunks/

# 注入的 helper（在文件顶部 "use strict"; 之后）
HELPER = ('function __c$(n,p){var d=(document.cookie.match(/locale=([^;]+)/)||[])[1]||"";'
          'return /zh/i.test(d)?("\u00a5"+((n||0)*7.2).toFixed(p||2)):("$"+((n||0).toFixed(p||2)))};')

# 4 处替换（old -> new）
REPLACEMENTS = [
    # 1. Est. Cost 预估成本 (~$X.XX)
    ('(t=e.totalCost,`$${(t||0).toFixed(2)}`)',
     '(t=e.totalCost,__c$(t))'),
    # 2. OverviewCards 概览卡片 formatter
    ('p=e=>`$${(e||0).toFixed(2)}`',
     'p=e=>__c$(e)'),
    # 3. UsageChart 图表 formatter (4 decimals)
    ('F=e=>`$${(e||0).toFixed(4)}`',
     'F=e=>__c$(e,4)'),
    # 4. Cost / call (4 decimals, with Free case)
    ('format:e=>0===e?"Free":`$${e.toFixed(4)}`',
     'format:e=>0===e?"Free":__c$(e,4)'),
]

def main():
    c = open(CHUNK, encoding="utf-8").read()
    # 1. 注入 helper（幂等：已注入则跳过）
    if "__c$" not in c:
        c = c.replace('"use strict";', '"use strict";' + HELPER, 1)
        print("[OK] helper 注入")
    else:
        print("[SKIP] helper 已存在")

    # 2. 应用替换
    for old, new in REPLACEMENTS:
        cnt = c.count(old)
        if cnt == 1:
            c = c.replace(old, new, 1)
            print(f"[OK] 替换: {old[:50]}... -> {new[:40]}")
        elif cnt == 0:
            print(f"[WARN] 未找到: {old[:50]}...")
        else:
            print(f"[WARN] 出现{cnt}次,跳过: {old[:50]}...")

    # 3. 写回（带备份）
    bak = CHUNK + f".currency.bak.{int(time.time())}"
    shutil.copy2(CHUNK, bak)
    open(CHUNK, "w", encoding="utf-8").write(c)
    print(f"\n[OK] 已写回, 备份: {bak}")

if __name__ == "__main__":
    main()
