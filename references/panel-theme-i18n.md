# fnOS Panel Frontend: Day/Night Theme + i18n (single-file, client-side)

Pattern for a zero-dep fnOS web panel (`app/www/index.html`) that ships day/night theme and CN/EN i18n **without any build step or framework** — pure vanilla JS in one file. Verified 2026-08 with the Strava Panel fnOS app (techysy/strava-fnos v1.0.1).

## Theme (day/night)
- CSS variables on `:root` (dark) + `[data-theme="light"]` override; every component color references a variable so one attribute flips the whole UI.
- Persist choice in `localStorage`; default to the OS preference on first visit.
```html
<style>
:root{ --bg:#0f1420; --card:#1a2130; --text:#e8edf5; --muted:#8a97ab; --brand:#fc4c02; --border:rgba(255,255,255,.06); }
[data-theme="light"]{ --bg:#f5f6fa; --card:#fff; --card2:#eef1f6; --text:#1a2130; --muted:#6b7686; --border:rgba(0,0,0,.08); }
</style>
```
```js
function applyTheme(t){ document.documentElement.setAttribute("data-theme", t);
  document.getElementById("themeBtn").textContent = t==="dark" ? "🌙" : "☀️"; }
function initTheme(){
  let s = localStorage.getItem("sv_theme");
  if(!s) s = (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) ? "light" : "dark";
  applyTheme(s);
}
function toggleTheme(){
  const n = (document.documentElement.getAttribute("data-theme")||"dark")==="dark" ? "light" : "dark";
  localStorage.setItem("sv_theme", n); applyTheme(n);
}
```
- Smooth via `body{transition:background .2s,color .2s}`.

## i18n (CN/EN)
- Put every translatable label behind a `data-i18n="key"` attribute; drive all copy from one dict per language.
- Persist `lang` in `localStorage` (default `zh` for this user).
```js
const I18N = {
  zh: { "setup.title":"⚙️ 配置 Strava 凭据", "badge.ok":"已连接 ✓", /* ... */ },
  en: { "setup.title":"⚙️ Configure Strava Credentials", "badge.ok":"Connected ✓", /* ... */ }
};
let lang = localStorage.getItem("sv_lang") || "zh";
function t(key){ const d = I18N[lang]||I18N.zh; return d[key]!==undefined ? d[key] : (I18N.zh[key]||key); }
function applyI18n(){
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el=>{ el.innerHTML = t(el.dataset.i18n); });
  document.getElementById("langBtn").textContent = lang==="zh" ? "EN" : "中文";
}
function toggleLang(){ lang = lang==="zh"?"en":"zh"; localStorage.setItem("sv_lang",lang); applyI18n(); refreshStatus(); }
```
- Header row: `<button class="lang-btn" id="langBtn" onclick="toggleLang()">EN</button>` + `<button class="icon-btn" id="themeBtn" onclick="toggleTheme()">🌙</button>`.
- For strings that contain HTML (e.g. a hint with a `<a href>`), store the raw HTML in the dict and use `el.innerHTML = t(...)` — NOT `textContent`, which would show the literal markup.

## Stats period toggle + derived column (annual/monthly, avg speed)

Small extension on the same single-file panel (Strava Panel v1.1.1) worth reusing when a panel shows aggregated stats and the user wants an explicit time boundary + a derived per-row field:

- **Period toggle**: a pair of `lang-btn` buttons ("本年度 / 本月份"). Track `let period = "year"`; on click call `setPeriod(p)` which highlights the active button (swap `border-color`/`color` to the brand var) and calls `loadData()` again. `loadData()` computes the period start client-side and passes it as the backend's date filter:
  ```js
  const y = new Date().getFullYear();
  const m = String(new Date().getMonth()+1).padStart(2,"0");
  let start = `${y}-01-01`;                       // annual (default)
  if (period === "month") start = `${y}-${m}-01`; // monthly
  fetch(API + `/api/stats?start=${start}`)
  ```
  The backend already supports `?start=`/`?end=` (see zero-dep-python-backend SQLite pattern) — the frontend just maps the toggle to a `start` date. Default to **annual** and make the active period visually explicit so the user always knows the boundary (the user's complaint was "no boundary, unclear whether annual or monthly").
- **Derived per-row field (avg speed)**: `average_speed` from Strava is in **m/s**; convert to km/h for display with `(a.average_speed||0)*3.6`. Add it as an extra `<th>`/`<td>` in the recent-rides table. Any per-row metric that's derivable from stored fields goes in the client render, not the backend.

## Notes
- Both prefs are per-browser (localStorage), so they live on the user's device, not the NAS — no backend or fpk change needed to alter defaults.
- Keep `onclick` handlers on a single script block at the bottom; no framework, no build — just drop the file into `app/www/`.
- `data-i18n` values MUST stay keyed consistently between the two language dicts or a label silently falls back to the zh/English default — add a fallback (`I18N.zh[key]||key`) so a missing key degrades gracefully instead of showing `undefined`.

## Two silent-breakage traps (hugo-blog-fnos manager.py 实测)

**坑 1：`map(t=>...)` 遮蔽 i18n 函数 `t()`。**
页面里 `t()` 是全局翻译函数，一旦哪处写了 `rows.map(t => ...)`，箭头参数 `t` 就遮蔽了全局 `t`——map 内再调 `t("...")` 实际调到的是数组元素，整段 JS 抛错**所有按钮失效**，且症状离案发现场很远（看起来像 i18n 坏了）。规则：array 回调参数**永远不要用单字母 `t`**，写 `r => ...` / `item => ...`。

**坑 2：`applyI18n()` 的 `innerHTML` 覆盖嵌套动态元素。**
`el.innerHTML = t(key)` 会重建容器内所有子节点。若 `data-i18n` 容器里嵌着 JS 动态更新的 span（如 `<h2 data-i18n="theme_title">🎨 主题管理 <span id="curTheme">…</span></h2>`），第一次 applyI18n 后 `#curTheme` 就没了 → 后续 `Cannot set properties of null`。规则：**动态元素必须放在 `data-i18n` 容器外面**（标题文字与计数/状态 span 拆开、平级）。

**坑 3：i18n 值不要带 emoji 图标。**
菜单项常是「icon span + 文本 span」结构；若 i18n 文案值本身也带同一个 emoji（`'restart':'🔄 重启内核'`），applyI18n 覆盖文本后与 icon span **叠加**成 `🔄🔄`。文案值只留纯文字，图标只归 icon span。
