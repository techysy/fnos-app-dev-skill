# fnOS manifest: developer/publisher convention + official icon radius

Durable conventions for packaging fnOS apps (verified against official apps like 百度网盘 and community tools).

## manifest developer/publisher (开发者/发布者)

The App Center detail page shows 开发者 (developer) and 发布者 (publisher) from these fields:

```
maintainer            = <upstream-project-or-your-name>
maintainer_url        = <upstream GitHub URL>
distributor           = <your-brand>
distributor_url       = <the app's OWN repo URL>
```

Rules (user's convention, 2026-08):
- **有上游项目 → maintainer = 上游** (the upstream project), `maintainer_url` = upstream GitHub.
  - 9router → `decolua` / `https://github.com/decolua`
  - metacubexd → `MetaCubeX` / `https://github.com/MetaCubeX`
  - hermes-webui → `NousResearch` / `https://github.com/NousResearch`
- **自己开发 → maintainer = 自己** (your own brand, e.g. `techysy`).
  - strava-panel → `techysy`
- **distributor 永远 = 自己品牌** (`techysy`)，`distributor_url` = **该应用自己的项目地址**（不是主页）— the user has many repos, so point the publisher link straight to the wrapped app's repo; users who want more can click through to the profile. Avoid pointing distributor_url at a not-yet-live site (e.g. techysy.com was deferred back to GitHub).

Official reference (百度网盘 app): `maintainer="百度网盘"`, `maintainer_url="https://pan.baidu.com/"`, `distributor="飞牛"`, `distributor_url="https://www.fnnas.com/"`. The manifest is **ini KEY=VALUE** (values may be quoted), NOT the JSON `{"developer","publisher"}` shape some docs show.

⚠️ manifest change requires **rebuild fpk + reinstall** before it shows in App Center.

## Official icon corner radius (官方圆角标准)

- 画布: **256×256px 正方形**
- **圆角半径 = 48px** = **边长的 18.75%**（标准正圆圆角，用 `arcTo`/`rounded_rectangle`，**不是苹果连续圆角 squircle**）
- 换算: 512→96px, 128→24px, 64→12px
- 佐证: 飞牛社区「在线 FPK 图标设计器」默认预设圆角 = 48px(256基准)，与官方原生图标一致
- ⚠️ 早期记录的 "fnOS 图标圆角很小 ~0-2.3%" 是**错误**的（那只是个别第三方应用的偏差）。官方标准就是 **18.75%**。
- In PIL: `ImageDraw.rounded_rectangle([0,0,w-1,h-1], radius=int(min(w,h)*0.1875))`

## Adding standard radius to an existing PNG (no generator script)

```python
from PIL import Image, ImageDraw
img = Image.open(src).convert("RGBA")
w,h = img.size
radius = max(2, int(min(w,h)*0.1875))
rounded = Image.new("RGBA",(w,h),(0,0,0,0))
ImageDraw.Draw(rounded).rounded_rectangle([0,0,w-1,h-1], radius=radius, fill=(255,255,255,255))
Image.composite(img, Image.new("RGBA",(w,h),(0,0,0,0)), rounded).save(dst)
```
Apply to all icon slots: `ICON.PNG`(64) `ICON_256.PNG`(256) `app/ui/images/icon_{64,128,256}.png`.

## Re-packaging an upstream-wrapped app preserves bundle hot-patches

When a fnOS app wraps an upstream whose built bundle has **hot-patches** (e.g. 9Router Cloudflare `authModes` + currency `__c$`), the fpk's `app/server` is NOT in the git repo — it's obtained either from `npm pack` (原始无补丁) or by **copying from the already-installed app**. To ship a fpk that already carries the patches:

```
rm -rf "/vol1/1000/fnOS Dev/<app>-fnos/app/server"
cp -r /vol4/@appcenter/<app>/server  "/vol1/1000/fnOS Dev/<app>-fnos/app/server"
```
Then `fnpack build`. Verify patches survive: `grep -c 'authModes:\["apikey"\]' app/server/.next-cli-build/server/chunks/2573.js` and `python3 -c "print(open(f).read().count('__c$'))"` on the currency chunk.

⚠️ **fpk reinstall wipes bundle patches** — if you package from a fresh `npm pack`/reinstall, the Cloudflare + currency patches are lost and must be re-applied (patch scripts live in the `<app>-fnos` repo `scripts/`). Also note a 9router orphan `next-server` process started by fnOS (9router user) can survive uninstall and hold port 20128 → "端口被占用" on reinstall; it needs root (`sudo kill -9`) or an fnOS restart to clear.
