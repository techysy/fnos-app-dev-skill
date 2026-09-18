# Zero-Dependency Python Backend for fnOS Apps

fnOS NAS has Python 3.11 but **no pip packages preinstalled** (no flask, no flask_cors, etc. — `import flask` fails). For a self-hosted app backend, use the **standard library only** (`http.server` / `socketserver`) — zero install, zero build steps, packages cleanly.

## When to use
- A backend API + static panel frontend, no heavy framework needed
- You can't/don't want to pip-install on the NAS (no venv, no network guarantee)
- Pattern verified 2026-08 with the Strava Panel fnOS app (techysy/strava-panel-fnos).

## Structure
```
app/
├── server/
│   └── app.py        # http.server backend (stdlib only)
└── www/
    └── index.html    # static frontend (served by app.py)
```
`cmd/main` runs `python3 app.py` with `DATA_DIR` + `PORT` env. Health check hits `/api/status`.

## app.py skeleton (key parts)
```python
import json, os, urllib.request, urllib.parse, http.server, socketserver
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "/tmp/app-data"))
WWW_DIR = Path(__file__).parent.parent / "www"

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence default stderr spam
        pass
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")  # CORS for iframe-embed
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def _send_file(self, rel):
        p = (WWW_DIR / rel).resolve()
        if not str(p).startswith(str(WWW_DIR.resolve())) or not p.exists():
            self.send_error(404); return
        ctype = {".html":"text/html; charset=utf-8", ".js":"application/javascript",
                 ".css":"text/css", ".svg":"image/svg+xml"}.get(p.suffix, "application/octet-stream")
        body = p.read_bytes()
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status": self._send_json({"ok": True})
        elif path in ("/", ""): self._send_file("index.html")
        else: self.send_error(404)
    def do_POST(self):
        # read body: length = int(self.headers.get("Content-Length",0)); self.rfile.read(length)
        pass

def main():
    port = int(os.environ.get("PORT", "8081"))
    httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), Handler)
    httpd.daemon_threads = True
    print(f"listening on {port}", flush=True)
    httpd.serve_forever()
```

## Notes / pitfalls
- `socketserver.ThreadingTCPServer` + `daemon_threads=True` → handles concurrent API calls (Strava fetches are slow, don't block the panel).
- **预设/系统资源双重保护**：应用自带不可删除的资源（如 `minimal` 主题）时，前端隐藏删除按钮**不够**——后端 API 也必须拒绝（`if name in PRESET: return False, "系统预置主题不能删除"`），否则 API 仍可直接打删。
- **agent 可发现的 bootstrap token 模式**：token 存数据目录 `api_token`（600 权限，`secrets.token_hex(16)` 生成）；`GET /api/bootstrap` 免认证返回 `{api_token}` 供 agent/前端首次获取；其余 `/api/*` 校验 `Authorization: Bearer <token>`，缺则 401。前端 `initToken()` 拉 bootstrap 后统一走带 Bearer 的 `apiFetch()` 包装——别在页面里硬编码 token。README 写清 curl 用法（先取 token 再带 Bearer）。
- 上传解析手写 multipart（`body.split(b"--"+boundary)`），**不要用 `cgi.FieldStorage`**（Python 3.13 已移除，3.11+ 弃用且报 "Cannot be converted to bool"）。
- Always send `Access-Control-Allow-Origin: *` on API responses → helps iframe-embedded (`type:"iframe"`) panels avoid CORS blocks (though fnOS container iframe CORS can still be an issue at the container layer; `type:"url"` is safest).
- CWD = `SRC_DIR` (set by cmd/main via `cd`), so `WWW_DIR = Path(__file__).parent.parent/"www"` resolves correctly regardless of where fnOS launches it.
- `print(..., flush=True)` startup banner so the log shows the port + DATA_DIR immediately.
- **`python3 -u` (unbuffered) for background start — use it in `cmd/main`.** Plain `python3 app.py` under `nohup ... &` / `setsid ... &` can fail with a baffling `OSError: [Errno 98] Address already in use` in the app log EVEN WHEN `ss -tln | grep <port>` shows NO listener and `lsof -i :<port>` is empty. The port is genuinely free (a standalone bind test succeeds), so it's not a real occupancy — it's the backgrounding wrapper racing/flushing. Foreground-run (`timeout 5 python3 -u app.py`) always works. Switching cmd/main to `python3 -u app.py` + `setsid ... < /dev/null &` made the exact same backend start reliably every time. Add `-u` to the launch command as a default habit.

  **⚠️ THE DECISIVE FIX — `SO_REUSEADDR` on `ThreadingTCPServer` (2026-08, Strava Panel v1.1.4).** Even after the `-u`+setsid change, the "Address already in use but port is free" paradox **kept coming back** under fnOS App Center restarts — the classic cause is **`TIME_WAIT` sockets left over from frequent stop/start** (`ss -tan | grep <port>` shows `TIME_WAIT` entries even when nothing is listening). `socketserver.ThreadingTCPServer` defaults to `allow_reuse_address = False`, so it does NOT set `SO_REUSEADDR`, and a `bind()` against a port with a lingering `TIME_WAIT` connection fails with `Address already in use` — even though `ss -tln`/`lsof`/a fresh standalone `socket.bind()` all look free (a NEW socket bound outside the server doesn't hit the TIME_WAIT collision; the server's fresh socket does). The reliable fix is to set the class attribute **BEFORE constructing the server** (socketserver reads `allow_reuse_address` in `__init__` during `server_bind`, so setting it on the *instance* after construction is TOO LATE):
  ```python
  import socketserver
  socketserver.ThreadingTCPServer.allow_reuse_address = True   # ← before constructing
  httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), Handler)
  ```
  After this, rapid restart (kill → immediately relaunch) binds cleanly every time. Do this in ANY fnOS stdlib-Python backend that gets restarted (fnOS 启用/停用, upgrade, NAS reboot) — it eliminates a whole class of "port free but won't bind" flakiness that looks random. This is the real root cause the `-u`/setsid change only partially masked; `-u` still matters, but `SO_REUSEADDR` is what finally made the persistent case deterministic.

  **When the "Address already in use but port is free" paradox persists, run this decisive debug sequence** (flaky background-start makes naive retries look random; confirm the real cause before editing cmd/main):
  1. Prove the port is genuinely free (no hidden/TIME_WAIT bind): `ss -tan | grep <port>` should be empty, then a standalone `python3 -c "import socket;s=socket.socket();s.bind(('0.0.0.0',<port>));s.close()"` should not raise.
  2. Trace exactly what cmd/main does and spot a stray pkill or port-check false-positive: `bash -x /var/apps/<App>/cmd/main start 2>&1 | grep -iE "port|python3|pkill|setsid|ERROR|already"`.
  3. Foreground-run the real app to confirm it CAN bind: `cd <SRC_DIR> && timeout 5 env DATA_DIR=/vol4/@appdata/<App> PORT=<port> python3 -u app.py`. If this succeeds, the app is fine and the failure is the background wrapper (the `-u`/setsid fix).
  4. Confirm the port is fully idle, then clean retry via cmd/main.
  The most common real cause at the tail of a long session is a **stale manually-started process** (a different user, e.g. `<user>`, started `python3 app.py` by hand earlier) still holding the port invisibly to App Center. Note: `pkill -f "python3 app.py"` in cmd/main's `kill_all` does NOT match a running `python3 -u app.py` (the `-u` changes the cmdline), so when you add `-u` to the launch you must ALSO add a matching `pkill -f "python3 -u app.py"` (or a broader `pkill -f "app.py"`) so `start` can reap its own stale instance.
- Verify locally BEFORE building the fpk: run `DATA_DIR=/tmp/x PORT=<port> python3 app.py` from a terminal background, curl the endpoints, then kill it. Do this with the EXACT env fnOS passes (esp. `TRIM_APPDEST` → see DATA_DIR pitfall in SKILL.md). First Strava sync of a full history is slow (>60s for ~1100 activities / 12 pages) — the curl client may time out even though the sync completes server-side; re-curl `/api/sync` (now idempotent, `new:0`) or check `last_sync` in the db to confirm it landed.

## cmd/main `status()` exit code decides whether fnOS auto-starts (v1.1.5, the real "never auto-starts" root cause)

fnOS polls `cmd/main status` (every ~30s) as the app user and keys off the **exit code**: `0` → app running, nonzero → stopped → fnOS then calls `start`. If your `status()` falls through and returns `0` even when stopped, fnOS thinks the app is already up and **never calls `start`** — service stays down, `ss` port closed, lifecycle log (`/var/log/apps/<App>.log`) repeats `stopped`/`running` with no error, and the diagnostic `call:` lines show only `status`/`stop`, never `start`. Sibling apps that auto-start (metacubexd, 9router) all end `status()` with `echo stopped; return 1`. Fix — every stopped branch must `return 1`:
```bash
status() {
  [ -f "${PID_FILE}" ] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null && { echo "running"; return 0; }
  curl -sf "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1 && { echo "running"; return 0; }
  echo "stopped"; return 1
}
```
Verify: `bash cmd/main status; echo $?` → `1` when stopped, matching a sibling. When the diagnostic log shows fnOS only ever issuing `status`/`stop` (never `start`), the cause is almost always this exit-code bug, not fnOS refusing to manage the app.

## SQLite cache + agent-exposed API (v1.1 Strava Panel pattern)

When the backend pulls from a rate-limited external API (Strava, etc.) and you want **local fast reads, offline history, AND to expose the data to a local agent**, add a stdlib `sqlite3` cache layer and HTTP query endpoints. Still zero pip deps — `sqlite3` is stdlib. Verified 2026-08 with Strava Panel v1.1 (techysy/strava-panel-fnos).

**DB schema** — create idempotently on EVERY connect (robust against the db file being deleted/recreated while the process stays up):
```python
import sqlite3
def _conn():
    conn = sqlite3.connect(DB_FILE)   # DB_FILE = DATA_DIR / "strava.db"
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY, name TEXT, type TEXT, distance REAL, moving_time REAL, total_elevation_gain REAL, start_date TEXT, elapsed_time REAL, average_speed REAL, max_speed REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_start_date ON activities(start_date)")
    return conn
```
Put the `CREATE TABLE IF NOT EXISTS` in `_conn()` (not only `__init__`) — a `count()` on a wiped file would otherwise raise `sqlite3.OperationalError: no such table`. (Hit this locally after deleting the test db with the process still running.)

**Sync (external API → SQLite)** — paginate upstream into `INSERT OR REPLACE ... BY id`, record `last_sync` in `meta`. Aggregate stats / weekly with SQL `SUM/COUNT` + ISO-week grouping from SQLite — do NOT re-fetch upstream for reads (that defeats the cache).

**Agent-facing endpoints** — reads hit the cache (fast); `/api/sync` triggers a manual re-pull; `/api/export?fmt=json|csv` dumps everything for a local agent:
```
GET /api/stats?start=&end=           # totals + weekly, from SQLite
GET /api/activities?type=Ride&limit=&start=&end=
GET /api/weekly
GET /api/sync                         # manual re-pull
GET /api/export?fmt=json|csv          # full dump for agent
```
- Auto-sync once when the db is empty; `/api/status` reports `db_activities` count + `last_sync` so the panel/agent can judge cache freshness.
- Use ISO `start_date`/`end_date` SQL filters (`start_date >= ?`, `start_date <= ?+'T23:59:59'`) so an agent can cheaply query "this month".
- CSV export returns `Content-Disposition: attachment` with a header row. Document the curl examples in the README so a local agent self-serves without re-implementing the upstream OAuth: `curl ".../api/stats?start=2026-07-01&end=2026-07-31" | jq '.total_distance_km'`.

**Security** — `save_config`/token writes should `os.chmod(file, 0o600)` so Client Secret / Refresh Token aren't world-readable (the app-data dir can end up 644 if launched by the wrong user). The data dir holds live OAuth tokens, so treat it as sensitive.
