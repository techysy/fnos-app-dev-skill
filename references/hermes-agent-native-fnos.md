# Hermes Agent on fnOS - Native Installation

## Overview
Install Hermes Agent directly via pip on fnOS, bypassing the official trim.hermes app which has too many restrictions.

## Installation

### 1. Create venv
```bash
/usr/bin/python3 -m venv /home/<user>/hermes-env
```

### 2. Install hermes-agent
```bash
/home/<user>/hermes-env/bin/pip install hermes-agent
```

### 3. Verify
```bash
/home/<user>/hermes-env/bin/hermes --version
# Should show: Hermes Agent v0.19.0
```

## Configuration

### config.yaml (`~/.hermes/config.yaml`)
```yaml
model:
  default: mimo-v2.5
  provider: xiaomi
  base_url: https://api.xiaomimimo.com/v1
toolsets:
  - hermes-cli
agent:
  max_turns: 50
approvals:
  mode: manual
api_server:
  enabled: true
  host: "127.0.0.1"
  port: 18642
```

### .env (`~/.hermes/.env`)
```
XIAOMI_API_KEY=<YOUR_API_KEY>
API_SERVER_ENABLED=true
API_SERVER_HOST=127.0.0.1
API_SERVER_PORT=18642
API_SERVER_KEY=<local-key>
```

## Starting the Agent

### Manual Start
```bash
export HERMES_HOME=~/.hermes
export HOME=/home/<user>
/home/<user>/hermes-env/bin/python3 -m hermes_cli.main serve --host 127.0.0.1 --port 18642 --skip-build
```

### Systemd Service
```bash
hermes gateway install
hermes gateway start
```

## Connecting WebUI to Local Agent

### Method 1: hermes_home symlink
```bash
rm -rf /vol4/@appdata/HermesWebUI/hermes_home
ln -sf ~/.hermes /vol4/@appdata/HermesWebUI/hermes_home
```

### Method 2: gateway.env configuration
```bash
USE_REMOTE_GATEWAY="false"
DASHBOARD_URL="http://127.0.0.1:18642"
GATEWAY_URL="http://127.0.0.1:18642"
GATEWAY_KEY="<local-key>"
```

## Troubleshooting

### "PermissionError: [Errno 13] Permission denied"
hermes_home directories need write permissions:
```bash
chmod -R 777 ~/.hermes
```

### Gateway not listening on port
1. Check `.env` has `API_SERVER_ENABLED=true` and `API_SERVER_KEY` set
2. Check `config.yaml` has `api_server:` section
3. Restart gateway: `hermes gateway restart`

### "aiohttp not installed" warning
This is a false positive - aiohttp IS installed. The Gateway runs but the API server adapter doesn't load. Fix: ensure both `.env` and `config.yaml` have API server configuration.
