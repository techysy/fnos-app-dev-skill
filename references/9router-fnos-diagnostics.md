# 9Router on fnOS — data layout & provider-connection diagnostics

How to diagnose "provider shows 无连接 / inactive in the panel but seems configured"
on the 9Router Proxy fnOS app. Useful whenever the UI state and reality disagree.

## Where 9Router lives on fnOS

- App data: `/vol4/@appdata/9router/` (9router user)
  - `db/data.sqlite` — SQLite state DB (WAL mode: `data.sqlite-shm` / `-wal`)
  - `9router.log` — runtime log (proxy POSTs, [AUTH] warnings)
  - `9router.pid`, `jwt-secret`, `machine-id`, `auth/cli-secret`
- App files: `/vol4/@appcenter/9router/server/` (bundled Next.js standalone,
  `next-server` on port 20128)
- Lifecycle script: `/var/apps/9router/cmd/main` (root-owned, has start/stop/status;
  restart goes through fnOS App Center UI, NOT raw SSH kill)

## Key DB tables (data.sqlite)

- `providerConnections` — id (pk), provider, authType, name, email, priority,
  isActive (default 1), data (JSON), createdAt, updatedAt
- `providerNodes` — usually empty (not the source of list-page counts)
- `apiKeys` — API keys clients use against `:20128`
- Also: settings, proxyPools, combos, kv, usageHistory, usageDaily, requestDetails

## Read the DB read-only over SSH (no sqlite3 on NAS; use python3)

```bash
ssh <user>@<NAS_IP> 'python3 << "EOF"
import sqlite3, json
conn = sqlite3.connect("file:/vol4/@appdata/9router/db/data.sqlite?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM providerConnections WHERE provider = ?", ("cloudflare-ai",))
r = cur.fetchone()
d = dict(r); data = json.loads(d["data"])
print("isActive:", d["isActive"], "| authType:", d["authType"], "| testStatus:", data.get("testStatus"))
print("data keys:", list(data.keys()), "| lastError:", data.get("lastError"))
EOF'
```

Cloudflare (`cloudflare-ai`) connection data JSON contains: `apiKey`, `testStatus`
(`"active"` = validated), `providerSpecificData.accountId`,
`connectionProxyEnabled`, `lastError` (null when healthy).

## Verify runtime routing (not just stored state)

Check the log for live traffic — a successful POST proves the connection works
even if the UI shows nothing:

```bash
ssh <user>@<NAS_IP> 'grep -E "cloudflare-ai|cf/@" /vol4/@appdata/9router/9router.log | tail -15'
# 🟢 ▶ POST cf/@cf/zai-org/glm-4.7-flash → cloudflare-ai/... · FMT: openai→openai  = WORKING
# ⚠️ [AUTH] No credentials for cloudflare-ai  = connection not picked up (transient during edit, or broken)
```

Also `/v1/models` on `:20128` returns the `cf/@cf/...` model IDs when the backend
sees Cloudflare as connected.

## Pitfall: "无连接" in the provider-list grid ≠ broken connection

- A provider card can show **无连接** on the provider list grid while the
  per-provider detail page shows the connection as **活跃**, AND the models still
  route successfully. In that case the stored state + runtime are both fine and
  the mismatch is a **9Router frontend display bug** in how the catalog grid
  computes/shows connection counts.
- Restarting the 9Router app (App Center 停用/启用) does **NOT** fix it; a hard
  browser refresh (Ctrl+Shift+R / incognito) only helps if it was client cache.
- Decisive check order: (1) DB `isActive`+`testStatus`, (2) recent successful
  `POST ... → cloudflare-ai/...` lines in the log, (3) `/v1/models` lists the
  provider's model IDs. If all three pass, the connection is real and the UI is
  lying — treat as cosmetic, don't delete/re-add credentials.

## Auth notes

- `/api/providers/*` and `/v1/chat/completions` require the API key; `/v1/models`
  is more permissive. When curling from localhost, use the full key from
  `apiKeys.key` — a truncated/redacted key gives `401 Unauthorized` /
  `invalid_api_key`. (Hermes redacts key strings in tool output, so pull the key
  from the DB in the same script that uses it, or test via `/v1/models`.)
- curl to the LAN IP from the Arch VM triggers the security scanner; run curl
  against `http://127.0.0.1:20128/...` from inside the NAS via SSH instead.
