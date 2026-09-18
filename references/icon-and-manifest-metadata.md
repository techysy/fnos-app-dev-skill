# fnOS 图标圆角标准 与 manifest 开发者/发布者规范

## 官方图标圆角标准（权威，来自飞牛社区「在线 FPK 图标设计器」+ 官方原生应用）

- **画布**：256×256px 正方形
- **圆角半径 = 48px**（标准正圆圆角，**不是苹果连续圆角 squircle**）
- 比例换算：**圆角 = 画布边长 × 18.75%**
  - 512×512px → 96px
  - 128×128px → 24px
- ⚠️ 早期"fnOS 图标圆角很小 ~0-2.3%"的说法是**错误**的（那只是个别第三方应用的偏差）。官方标准就是 **18.75%**。
- 用户明确要求：**大圆角是预期**，生成脚本用 `rounded_rectangle(radius = int(size * 0.1875))`。

## 实测圆角测量

NAS 上无 PIL 时，用纯 Python + zlib 解码 PNG alpha 通道测圆角（`scripts/measure-icon-radius.py`，见脚本）。

## fnpackup（在线打包工具）的圆角处理

- `fnpackup`（snltty/fnpackup，github.com/snltty/fnpackup）是 fnpack 的可视化 UI，**没有内置 18.75% 预设**，圆角用滑块手动调（0~size/2）。
- 它的 `createRoundedRectPath` 用 `arcTo` 画**标准正圆圆角**——**佐证**官方"标准圆角非 squircle"的说法。
- 额外功能：纯静态网页托管（`fnpackup=` manifest 字段 + `http://ip:1069/{appname}`），对纯静态 fpk 有用，但对带后端服务的应用无帮助。

## manifest 开发者/发布者规范（参考官方百度网盘）

官方 manifest 用 ini 格式（非 JSON），关键字段：

```ini
maintainer            = "开发者名"
maintainer_url        = "https://...开发者链接"
distributor           = "发布者名"
distributor_url       = "https://...发布者链接"
helpurl               = "https://..."
```

参考：百度网盘 `maintainer="百度网盘"` / `maintainer_url="https://pan.baidu.com/"` / `distributor="飞牛"` / `distributor_url="https://www.fnnas.com/"`。

**开发者/发布者填写的约定（用户明确要求）**：
- **有上游项目** → 开发者 = 上游作者（9router→`decolua`，metacubexd→`MetaCubeX`，hermes-webui→`NousResearch`），distributor 仍是打包者自己（<user>/techysy）
- **自己开发** → 开发者 + 发布者都填自己（strava-panel→`<user>`）

已应用示例：
| 应用 | maintainer | distributor |
|------|-----------|-------------|
| strava-panel | <user> (github.com/techysy) | <user> |
| 9router | decolua (github.com/decolua) | <user> |
| metacubexd | MetaCubeX (github.com/MetaCubeX) | <user> |
| hermes-webui | NousResearch (github.com/NousResearch) | techysy |

⚠️ 改 manifest 后需**重新打包 fpk 并重装**才会在 App Center 详情页生效。
