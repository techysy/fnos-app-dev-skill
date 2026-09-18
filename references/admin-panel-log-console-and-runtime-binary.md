# fnOS Admin Panel: Log Console + Packaging External Runtimes

Two reusable patterns for fnOS apps that wrap a service + a Python admin panel
(`server/manager.py`, a stdlib-only `http.server`). Both were implemented in the
hugo-blog-fnos app (v0.1.4).

## 1. Admin-panel "控制台" log console (date-archived)

Give the management panel a console tab that shows the app's logs, archived by day,
with refresh + download. Pattern:

### Backend (manager.py)
- Keep an explicit log-source map so new logs are easy to add:
  ```python
  LOG_SOURCES = {"hugo": DATA_DIR / "hugo.log", "manager": DATA_DIR / "manager.log"}
  LOG_ARCHIVE_DIR = DATA_DIR / "logs"   # archived `logs/<name>.log.YYYYMMDD`
  ```
- `archive_logs()` runs at manager startup: if a current log file's mtime is NOT
  today, append its bytes into `logs/<name>.log.<YYYYMMDD>` and truncate the working
  file to empty. Only non-today files are rolled (today's stays in the working file
  so `/api/logs` tail works).
- `list_log_dates(name)` scans `logs/<name>.log.[0-9]*` plus the current file →
  returns `[{date: "YYYYMMDD", display: "YYYY-MM-DD"}]` sorted desc, deduped.
- `read_logs(name, date=None, tail=N)`: if `date` given, read the archived file;
  else the current file; slice to last N lines.
- HTTP endpoints (all behind the existing Bearer-token auth):
  - `GET /api/logs/list?source=hugo` → `{sources:[...], dates:[...], current}`
  - `GET /api/logs?source=hugo&date=YYYYMMDD&tail=2000` → `{source,date,display,total,content}`
  - `GET /api/logs/download?source=hugo&date=...` → text/plain with `Content-Disposition: attachment`

### Frontend (INDEX_HTML)
- Sidebar nav item + a `tab-console` panel with: source `<select>`, date `<select>`
  (options from `/api/logs/list`), refresh + download buttons, and a `<pre id="logView">`
  (monospace, `white-space:pre-wrap`, scrollable).
- On nav switch to console → call `loadLogDates()`; changing source → reload dates;
  changing date → reload content; `downloadLog()` → `window.open('/api/logs/download?...')`.

## 2. Packaging an external runtime binary (dart-sass) into the app

When the wrapped service needs an extra tool on PATH (e.g. Hugo extended needs
`dart-sass`/`sass` to compile SCSS in `hugo server` mode):
- Place the standalone binary dir under `app/server/<tool>/` so it ships inside
  `app.tgz` at `server/<tool>/` (verified with `tar tzf app.tgz | grep <tool>`).
- In `cmd/main`, after resolving `SRC_DIR`, probe and prepend to PATH:
  ```bash
  DART_SASS_DIR=""
  for c in "${SRC_DIR}/dart-sass" "/vol4/@appcenter/<app>/server/dart-sass"; do
      [ -x "${c}/sass" ] && { DART_SASS_DIR="${c}"; break; }
  done
  [ -n "${DART_SASS_DIR}" ] && export PATH="${DART_SASS_DIR}:${PATH}"
  ```
- dart-sass standalone keeps `sass` (sh wrapper) + `src/` together; the wrapper
  resolves its own path via `$0`, so ship the whole dir intact and `chmod +x` both.
- Test with the SAME command mode the app actually runs (hugo `server`, not `hugo`).
  One-shot builds can pass while `server` mode still fails with TOCSS-DART.

## 3. "无法启用" / won't-start debugging for a wrapped service app

When App Center reports 无法启用 but the service "looks" up:
- Read the app's own logs, not just `systemctl status` / port checks:
  `DATA_DIR/hugo-diag.log` (cmd/main call trace incl. which USER called start),
  `DATA_DIR/hugo.log` (the actual service output — where render/SCSS errors surface).
- Distinguish a **manual systemd service** that shares the app name from the real
  App Center app. A hand-made `hugo-blog.service` (older mtime than the app install)
  running a DIFFERENT dir/port can mask or confuse `systemctl start hugo-blog`.
  App Center apps live at `/var/apps/<app>/` (cmd/main here, `target -> /vol4/@appcenter/<app>`);
  the standard-format apps run under `/usr/local/apps/@appcenter/<app>`.
- Root cause here was a SCSS theme needing Dart Sass → hugo server crashed on render
  → port never listened → 无法启用. Fix = either switch to a no-SCSS theme (minimal)
  or ship dart-sass (pattern 2).
