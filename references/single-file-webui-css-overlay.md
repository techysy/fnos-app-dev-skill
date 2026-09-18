# 单文件 WebUI 卡片内联编辑：CSS 覆盖层(不撑大网格)

背景：`hermes-core-fnos` 的状态页是单个 `cmd/status_server.py`（纯 stdlib, HTTP 服务直接输出整页 HTML/CSS/JS）。其中「模型供应商」面板用 CSS Grid 渲染卡片，点击卡片需内联编辑 API Key。

## 痛点
在卡片内用**文档流内**插入编辑区（`margin-top` + 块级输入框）会**撑高**卡片。因为网格是
`repeat(auto-fill, minmax(200px,1fr))`，同行的所有卡片会被强制拉伸到与最高的卡片等高 →
视觉上"撑大"、"错位"。用户明确要求：编辑区直接在**原卡片容器内**，不撑大。

## 解法：绝对定位覆盖层
让编辑区 `position:absolute` 铺满卡片本身，卡片尺寸完全不变，编辑 UI 浮在卡片内容上。

```css
.provider-card { position:relative; }                       /* 卡片须相对定位 */
.p-edit {
  position:absolute; top:0; left:0; right:0; bottom:0; z-index:5;
  background:var(--card); border-radius:12px; padding:12px;
  display:flex; flex-direction:column; justify-content:center;
  box-shadow:0 2px 12px var(--shadow);
}
.p-edit-input { width:100%; padding:7px 9px; box-sizing:border-box; margin-bottom:8px; }
.p-edit-btns { display:flex; gap:8px; }
.p-edit-btns button { flex:1; padding:7px 0; font-size:12px; }
```

## 关键坑：点击冒泡
若卡片整体带 `onclick="editProvider(key)"`（toggle 展开），点击编辑区内的输入框/保存/取消
会**冒泡到卡片** → 重新触发 toggle → 刚输入的 key 被重置、取消按钮"点了没反应"。

修复：编辑容器上 `stopPropagation`：
```js
edit.onclick = (e) => e.stopPropagation();
```
这样点击编辑区内不会重新触发卡片 toggle；点别的卡片才关闭当前编辑。

## 验证方法（重要）
视觉/浏览器截图模型会**误读**覆盖层场景：当编辑区覆盖卡片内容、输入框聚焦时，截图模型常误报
"卡片变窄/收缩/错位"，但 DOM 测量是唯一真相。用 `getBoundingClientRect()` 断言：
```js
[...document.querySelectorAll('.provider-card')].map(c=>c.getBoundingClientRect())
```
逐项确认：卡片宽/高在展开编辑**前后一致**，且所有卡片宽高相等（网格未被撑大/拉伸）。
切勿只信截图分析结论。

## 本地跑 status_server.py 快速自测
单文件可脱离 fnOS 直接起：
```bash
STATUS_PORT=8650 CORE_CONFIG=/tmp/test.env CORE_CMD=/bin/true STATUS_HOST=127.0.0.1 \
  python3 cmd/status_server.py
# 然后浏览器打开 http://127.0.0.1:8650/ ，用 console 执行 editProvider('9router') 验证
```
