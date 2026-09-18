# Python .format() 模板里嵌入 JS：反斜杠转义坑

## 现象
status_server.py 这类单文件 Python 把整段 HTML+JS 放在 `PAGE = """..."""` 里，最后 `PAGE.format(...)` 渲染。JS 字符串里的 `'\n'`（反斜杠+n）在 Python 三引号解析时**变成真换行符 (0x0A)**，导致生成的 JS 字符串跨行、`node --check` 报语法错误 / 浏览器 JS 崩溃。

## 变体坑：JS 字符串里的撇号（会让整段 script 全崩，所有按钮失效）
除换行转义外，**撇号（apostrophe）**是另一种致命坑。症状吓人：**页面所有按钮全部失效**（保存/重启/扫码/聊天/主题切换都不响应），因为整段 `<script>` 语法错误，脚本一行都没执行。

- 想在 i18n 里给 JS 一个转义撇号，源码写 `wxqr-open` 值为 `Can` + 反斜杠 + 撇号 + `t`
- 经 Python 三引号 + `.format()` 处理，反斜杠被吞，生成的 JS 变成**未转义撇号**，提前终止字符串字面量 → `SyntaxError` → 整段 JS 崩
- **根因**：反斜杠转义在 Python 字符串解析 / `.format()` 路径里不可靠，JS 侧拿不到预期的转义
- **最安全修法**：**别在 JS 字符串里用撇号/反斜杠转义**。改写文案避开撇号，例如 `Can` + apostrophe + `t` 直接改写成 `Cannot`。需要转义就用双引号 `"..."` 包不含双引号的串，或干脆避免特殊字符
- **验证（决定性的）**：渲染页面后提取 `<script>` 内容写文件，`node --check` 通过才说明 JS 语法对——浏览器崩溃前先自查
- **教训**：在 Python `.format()` 模板里嵌 JS，**任何反斜杠转义都不可靠**。优先用不含特殊字符的措辞；需要换行用上面 `\\n` 双反斜杠写法，需要撇号就直接避开

## 根因
- 源码 `'\n'`（单反斜杠+n）在 Python 三引号字符串里是**转义序列** → 解析成真换行符
- 要让生成的 JS 得到字面 `\n`（反斜杠+n 字符，JS 里表示换行转义），源码必须写 `'\\n'`（**双反斜杠**）
- 同理所有 JS/CSS 里的花括号 `{ }` 必须双写 `{{ }}`（`.format()` 转义），否则 `KeyError`

## 诊断（决定性的确认方法）
不要只靠眼睛看文本——用 **od/hex 看字节**，或 Python `repr`：
```python
# 服务器返回的 HTML 字节
b=open('page.html','rb').read(); i=b.find(b'indexOf')
print(b[i:i+15].hex(' '))   # 应见 5c 6e（反斜杠+n）；若见 0a 0a（真 LF）则转义错
```
- 反斜杠+n 两字符 = `5c 6e` ✓
- 真换行 = `0a` ✗

**注意**：Python `repr` 会把真换行显示成 `\n`，把反斜杠+n 显示成 `\\n`——容易被误读。用 `.hex(' ')` 最可靠。

## 修复
源码里把 JS 需要的 `\n` 写成 `\\n`：
```python
# PAGE = """ ... while ((idx = buf.indexOf('\\n\\n')) !== -1) {{ ... """
# 源码写双反斜杠 \\n，.format() 输出后 JS 得到字面 \n（正确换行转义）
```

## 验证
1. `python3 -c "import ast; ast.parse(open('x.py').read())"` — Python 语法 OK
2. 本地启动 `python3 x.py` + curl 拿 HTML，用 `.hex(' ')` 确认 `5c 6e`
3. 提取 `<script>` 内容写文件，`node --check` 通过

## 变体坑：模板字符串里嵌 `onclick="fn('arg')"` 别用反斜杠转义撇号
JS 模板字符串（反引号）里要生成 `<button onclick="fn('名称')">`，别写成 `onclick=\"fn(\\''+x+'\\')\"`（反斜杠+撇号在 Python 三引号里转义不可靠，浏览器拿到 `''` 双撇号 → `SyntaxError: Unexpected string` → 整段 script 崩，所有 tab/按钮失效）。
**修复**：用模板字符串插值直接嵌，撇号不需要转义：
```js
`<button class="btn" onclick="fn('${name}')">使用</button>`
```
教训同前：Python 三引号嵌 JS，**任何反斜杠转义都不可靠**；模板字符串里直接用 `${}` 插值最安全。

## 变体坑：i18n 值里带 emoji → applyI18n() 导致图标重复
这类状态页常有「图标 span + 文本 span」的菜单项，如：
```html
<span class="menu-ico">🔄</span><span data-i18n="restart">重启内核</span>
```
**坑**：若 i18n 值本身也带同一个 emoji（`'restart':'🔄 重启内核'`），`applyI18n()` 会把文本 span 的 `textContent` 替换成 `🔄 重启内核`，与前面的 icon span 🔄 **叠加**，最终渲染成 `🔄🔄 重启内核`（两个图标）。
**根因**：`applyI18n()` 用 `el.textContent = val` 直接覆盖，不会去重已单独渲染的图标。
**修复**：i18n 的 `textContent` 值**不要带 emoji**，只保留纯文字；图标只由专门的 icon span 渲染。排查时 `grep -c "onclick=\"X()\""` 数出的是「按钮 onclick + 函数定义」两处（会误以为重复），要精确数按钮用 `grep -c 'onclick="X()"'` 对比 `grep -c "function X"` 分开看。

## 大坑：旧进程没杀干净导致"改了不生效"
调试这类问题时，`pkill -9 -f "status_server.py"` 可能把**新的启动命令自身**也匹配杀掉（命令字符串里含文件名），且旧进程残留占端口，导致你测的永远是旧代码。必须：
- `pkill -9 -f "status_server.py"` 后 `ps aux | grep status_server.py | grep -v grep` 确认为空
- `ss -tlnp | grep <port>` 确认端口释放
- 用全新端口（递增）启动，避免撞残留
