# 9Router Proxy (fnOS app) debugging & hot-patching

9Router is a Next.js standalone app packaged as an fnOS app. Installed layout
(fnOS 1.1.31xx, verified 2026-08-01):

```
/vol4/@appcenter/9router/          TRIM_APPDEST (real files)
  server/                          Next.js standalone build
    custom-server.js               node entry (PORT from env, default 3000 → fnOS sets 20128)
    server.js                      next standalone launcher
    .next-cli-build/
      server/                      server-side chunks + API route handlers
      static/chunks/               client bundles served to browser
  cmd/main                         lifecycle (start/stop/status) — lives at /var/apps/9router/cmd/main
/vol4/@appdata/9router/            TRIM_PKGVAR (runtime data)
  db/data.sqlite                   SQLite: providerConnections, providerNodes, apiKeys, combos, kv, usage...
  auth/cli-secret
  9router.log                      runtime log
```

Service runs as user `9router` on port 20128 (`0.0.0.0:20128`). Process: `next-server`.

## Key DB tables

- `providerConnections` — columns: id, provider, authType, name, email, priority,
  isActive(1=on), data(JSON), createdAt, updatedAt. `data.testStatus` = "active" for a healthy conn.
- `apiKeys` — the router API keys (e.g. `<<YOUR_API_KEY>>`) used with `Authorization: Bearer`.
- `providerNodes` — custom provider node overrides (usually empty).

Read the DB read-only with Python (no sqlite3 CLI on NAS):
```bash
ssh <user>@<NAS_IP> 'python3 - <<PY
import sqlite3
c=sqlite3.connect("file:/vol4/@appdata/9router/db/data.sqlite?mode=ro", uri=True)
c.row_factory=sqlite3.Row
print([dict(r) for r in c.execute("SELECT * FROM providerConnections")])
PY'
```
(Hermes redacts long keys in tool output — use data.keys() instead of printing apiKey.)

## Diagnosing "provider shows 无连接 but detail shows 活跃"

Symptom: provider catalog grid card shows "无连接" while the provider detail page
shows an active connection, and `/v1/models` lists the provider's models.

1. Confirm the connection is genuinely active & routing:
   ```bash
   # models present?
   curl -s http://127.0.0.1:20128/v1/models -H "Authorization: Bearer sk-..." 
   # routed traffic in log?
   grep -E "cloudflare|cf/@" /vol4/@appdata/9router/9router.log | tail
   # DB state: isActive=1, data.testStatus="active"
   ```
   "No credentials for X" lines are transient (during add/edit); follow-up
   `POST ... → X/...` lines prove it works.

2. **ROOT CAUSE is almost always a missing `authModes` in the provider catalog def.**
   The provider grid counts a connection as connected only if its `authType` is in
   the catalog def's `authModes`. Missing `authModes` → grid resolves to `["oauth"]`
   → any `apikey`-typed connection is filtered out → card shows "无连接".

   The grid component (client bundle) logic:
   ```js
   M=(e,t)=>{if("kiro"===t)return["oauth","apikey","api_key"];
     let r=e?.authModes;
     return Array.isArray(r)&&r.includes("apikey")?["oauth","apikey","api_key"]:"oauth"}
   U=(e,t)=>{let a=conns.filter(c=>c.provider===e&&t.includes(c.authType)); /* connected=count of testStatus active/success */}
   ```
   Compare the broken provider against a working one in the same category
   (e.g. NVIDIA NIM has `authModes:["apikey"]`, Cloudflare did not).

## Hot-patching the catalog definition

The provider catalog lives in minified bundles. For a display bug, patch the
**client bundle** (grid renders in browser). Patch the **server chunk** too for
server-side parity.

Find the client bundle containing the provider def:
```bash
grep -rl 'id:"cloudflare-ai"' /vol4/@appcenter/9router/server/.next-cli-build/static/chunks/
grep -rl 'id:"cloudflare-ai"' /vol4/@appcenter/9router/server/.next-cli-build/server/chunks/
```

Patch by string replacement on a UNIQUE anchor (not the id alone — ids repeat
across aliases). For cloudflare the anchor was:
```
hasProviderSpecificData:!0,transport:{baseUrl:"https://api.cloudflare.com/client/v4/accounts/{accountId}/ai/v1/chat/completions"
```
→ insert `authModes:["apikey"],` after `hasProviderSpecificData:!0,`.

Script pattern (backup + replace, verify count==1):
```python
import shutil,time
anchor='hasProviderSpecificData:!0,transport:{baseUrl:"<UNIQUE_URL>"}'
repl  =anchor.replace('hasProviderSpecificData:!0,','hasProviderSpecificData:!0,authModes:["apikey"],',1)
c=open(path).read()
assert c.count(anchor)==1, c.count(anchor)
shutil.copy2(path, path+f".bak.{int(time.time())}")
open(path,"w").write(c.replace(anchor,repl,1))
```

Files are group-writable (rwxrwxr-x, `9router` group) — no sudo needed if the
ssh user is in the group.

Verify the server is serving the patched bundle:
```bash
curl -s "http://127.0.0.1:20128/_next/static/chunks/<file>.js" | grep -o 'cloudflare-ai.*authModes:\[.{0,20}'
```

## Pitfalls

- **Browser cache**: static chunks have hashed filenames served with immutable
  caching. After patching the client bundle, the user MUST hard-refresh
  (`Ctrl+Shift+R`) or the old JS still renders. No sw.js caching issue for
  static assets (the sw.js is push-notification only).
- **`sw.js` is notification-only** — don't expect it to serve stale chunks.
- **Upgrade wipes the patch**: any 9Router update rebuilds bundles and reverts
  the manual edit. Re-apply after upgrades; also file an upstream issue
  (the real bug is the missing `authModes` in 9Router's catalog source).
- **API auth for `/api/*` routes** uses session/login, not the `Authorization`
  Bearer key; only `/v1/*` and `/v1beta/*` proxy endpoints accept the API key.
  So you can probe `/v1/models` without logging in, but not `/api/providers`.
- **Restart via App Center UI, not SSH**: `cmd/main` is root-owned and sudo
  needs a password. Per user's hard requirement, fnOS app restart goes through
  the fnOS App Center (stop/start), not SSH.
- Use `ssh ... 'python3 - <<PY ... PY'` for multi-line Python on the NAS —
  `python3 -c` with nested quotes over SSH mangles. Write a `.py` to /tmp locally
  and `scp` it over when the script is complex.

## Faster diagnosis: clone upstream source for a readable reference

The NAS bundles are minified; the upstream repo is not. Cloning `decolua/9router`
(and reading `src/`) lets you find the exact catalog logic and definitions much
faster than reading the minified bundle:
```bash
gh repo clone decolua/9router /tmp/upstream -- --depth 1
grep -rn "cloudflare-ai\|dualAuthTypes" /tmp/upstream/src/
```
- Provider catalog definitions: `open-sse/providers/registry/<id>.js` (a local
  dir in the repo, NOT an npm dependency).
- Grid connection-count logic: `src/app/(dashboard)/dashboard/providers/page.js`
  → the `dualAuthTypes(info, key)` helper: returns `["oauth","apikey","api_key"]`
  only if `info.authModes` includes `"apikey"`, else `"oauth"`. That one function
  is the root of the "无连接 despite active connection" bug.
- `buildProviderEntry` in `src/shared/constants/providers.js` passes `authModes`
  through from the registry entry, so the fix belongs in the registry file, not
  the page.

This also gives you the exact file path + suggested fix to cite when filing the
upstream issue.

