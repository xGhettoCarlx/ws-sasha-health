# Sasha Health — Tailscale API proxy (Mac backend + DO edge)

## Architecture

```
Telegram Mini App / Browser
        │  HTTPS :8443
        ▼
DigitalOcean nginx  (youn8nbot.duckdns.org)
  /sh/     → static SPA  /var/www/sh/
  /api/    → proxy_pass  http://100.79.49.43:8000   (Mac via Tailscale)
        │
        ▼ Tailscale mesh
MacBook-Pro  (macbook-pro, 100.79.49.43)
  launchd com.sasha-health.backend
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  data/ lives only on Mac
```

## Mac

- Tailscale IPv4: `tailscale ip -4` (this host: **100.79.49.43**)
- LaunchAgent: `~/Library/LaunchAgents/com.sasha-health.backend.plist`
- Script: `scripts/run_backend.sh` (default `HOST=0.0.0.0`)
- `.env`: `HOST=0.0.0.0`, `PORT=8000`

Reload:

```bash
cp scripts/com.sasha-health.backend.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.sasha-health.backend 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.sasha-health.backend.plist
lsof -nP -iTCP:8000 -sTCP:LISTEN   # expect *:8000
```

## DO nginx

File: `/etc/nginx/sites-enabled/n8n` (server `youn8nbot.duckdns.org:8443`)

- `location /api/` → `http://100.79.49.43:8000` (keep URI path)
- `location = /api/health` → `http://100.79.49.43:8000/health`
- SPA: `location /sh/` → `/var/www/sh/`

After edit: `sudo nginx -t && sudo systemctl reload nginx`

## Frontend

`frontend/src/lib/api.ts`: `VITE_API_BASE` defaults to `""` → relative `/api/...`  
Same origin as Mini App URL → nginx proxies to Mac.

## Verify

```bash
# Mac
curl -s http://100.79.49.43:8000/health
# DO
curl -sk https://youn8nbot.duckdns.org:8443/api/health
curl -sk https://youn8nbot.duckdns.org:8443/api/overview | head
```
