# fnOS manifest 开发者/发布者 (developer/distributor) 约定

用户偏好 (2026-08, 适用于所有 fnOS 打包项目)。

## 规则

- **`maintainer` (开发者)**: 若打包的是上游项目，填**上游作者**；若是自己写的，填自己的品牌。
  - 9Router → `decolua`（上游 `decolua/9router`）
  - metacubexd → `MetaCubeX`（上游 `MetaCubeX/metacubexd`）
  - HermesWebUI → `NousResearch`（上游 `nesquena/hermes-webui`）
  - strava-panel → `techysy`（自己开发）
- **`distributor` (发布者)**: 统一填 `techysy`（打包者品牌）。
- **`maintainer_url`**: 上游项目 URL。
- **`distributor_url`**: **该应用自己的仓库 URL**（如 `https://github.com/techysy/9router-fnos`），**不是用户主页** —— 访问者直接落到具体项目，想看其他项目自然点主页。

## 示例 (strava-panel-fnos/manifest)

```ini
maintainer            = techysy
maintainer_url        = https://github.com/techysy/strava-panel-fnos
distributor           = techysy
distributor_url       = https://github.com/techysy/strava-panel-fnos
```

## 注意

- App Center 的「开发者/发布者」字段从 `maintainer`/`distributor` + 对应 `_url` 读取。
- 改动 manifest 需**重新打包 fpk + 重装**才显示。
- 链接应指向当前可用地址；若计划中的品牌站点（如 techysy.com）还没上线，先用 GitHub URL，上线后再切。
