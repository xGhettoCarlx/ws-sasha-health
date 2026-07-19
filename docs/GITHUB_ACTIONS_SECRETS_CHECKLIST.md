# GitHub Actions — Operator secrets checklist

**Pipeline:** `.github/workflows/deploy-sasha-health.yml`  
**App home:** `~/Station/mini_apps_studio/apps/sasha-health/`  
**Typical remote repo:** `ws-sasha-health` (app root = repo root)

> **SEC-BWS:** never put IPs, usernames, private keys, or server paths into YAML, commits, or chat logs. Configure them only under  
> **GitHub → Repository → Settings → Secrets and variables → Actions**.

---

## 1. Required repository secrets

Create these **Actions secrets** (names must match exactly):

| Secret name | Type | Purpose | Example shape (do not copy literally) |
|-------------|------|---------|----------------------------------------|
| **`DO_HOST`** | Secret | DigitalOcean droplet hostname or IP | `203.x.x.x` or `app.example.com` |
| **`DO_SSH_USER`** | Secret | SSH login user | `deploy` / `root` |
| **`DO_SSH_KEY`** | Secret | Full private key PEM for deploy user | `-----BEGIN OPENSSH PRIVATE KEY-----` … |
| **`DO_SPA_REMOTE_PATH`** | Secret | Remote directory for SPA static files (nginx root) | `/var/www/sh/` |

### Operator checklist — required

- [ ] `DO_HOST` set  
- [ ] `DO_SSH_USER` set  
- [ ] `DO_SSH_KEY` set (deploy-only key; not personal laptop key if avoidable)  
- [ ] `DO_SPA_REMOTE_PATH` set (must exist on server; trailing `/` recommended)  
- [ ] Deploy user can `rsync`/`ssh` to that path (permissions verified once by hand)

---

## 2. Optional secrets (recommended)

| Secret name | Purpose | Notes |
|-------------|---------|--------|
| **`DO_SSH_PORT`** | SSH port | Defaults to `22` if empty |
| **`DO_SSH_KNOWN_HOSTS`** | `ssh-keyscan` output for host pinning | Prefer over `accept-new` |
| **`DO_API_REMOTE_PATH`** | Remote path for FastAPI app tree | If empty → **SPA-only** deploy (legacy FE-only mode) |
| **`DO_POST_DEPLOY_CMD`** | Shell command after rsync | e.g. restart uvicorn/docker/supervisor |

### Operator checklist — optional

- [ ] `DO_SSH_PORT` (only if not 22)  
- [ ] `DO_SSH_KNOWN_HOSTS` (`ssh-keyscan -t ed25519,rsa <host>`)  
- [ ] `DO_API_REMOTE_PATH` (enable backend file sync)  
- [ ] `DO_POST_DEPLOY_CMD` (e.g. `sudo systemctl restart sasha-health` or `docker compose up -d --build`)  

---

## 3. Repository variables (non-secret)

**Settings → Secrets and variables → Actions → Variables**

| Variable | Required? | Purpose |
|----------|-----------|---------|
| **`SASHA_HEALTH_ROOT`** | Only for monorepos | Path to app inside repo: `apps/sasha-health` or `Projects/Project5`. Leave unset when app is repo root. |
| **`VITE_API_BASE`** | Optional | Frontend API base URL baked at build time |
| **`VITE_BOT_USERNAME`** | Optional | Telegram Login widget username |

### Operator checklist — variables

- [ ] If monorepo: `SASHA_HEALTH_ROOT` set  
- [ ] If standalone `ws-sasha-health`: leave `SASHA_HEALTH_ROOT` empty  
- [ ] `VITE_API_BASE` set if SPA and API are on different origins  

---

## 4. Server-side expectations (one-time)

- [ ] Nginx (or Caddy) serves SPA from `DO_SPA_REMOTE_PATH` under public path `/sh/` (or your chosen base; Vite `base` is `/sh/`)  
- [ ] API reverse-proxy to FastAPI if backend is used (`/api/` → uvicorn)  
- [ ] Runtime secrets on server (`.env` / vault) — **not** from this workflow  
- [ ] `data/` medical volume **not** overwritten by rsync (`--exclude data/` in pipeline)  
- [ ] Deploy key authorized in `~/.ssh/authorized_keys` for `DO_SSH_USER`  

---

## 5. Legacy secret names (migration map)

Older workflows used different names. Map them if reusing keys:

| Legacy secret | New secret |
|---------------|------------|
| `SSH_HOST` | → `DO_HOST` |
| `SSH_USER` | → `DO_SSH_USER` |
| `SSH_PRIVATE_KEY` | → `DO_SSH_KEY` |

Hard-coded paths like `/var/www/sasha-health` or `/var/www/sh/` now live only in **`DO_SPA_REMOTE_PATH`** (and optionally `DO_API_REMOTE_PATH`).

---

## 6. How to run

1. Push this app (with `.github/workflows/deploy-sasha-health.yml`) to the GitHub remote.  
2. Configure secrets above.  
3. Either:
   - push to `main` / `master` (paths under frontend/app/…), or  
   - **Actions → Deploy Sasha Health → Run workflow** (`workflow_dispatch`).  
4. Confirm green jobs: **Resolve → Backend tests → Build React SPA → Deploy to DO**.  
5. Hard-refresh Mini App; check `version.json` on the CDN/static host.

---

## 7. What the pipeline never does

- ❌ Print secret values  
- ❌ Commit or upload `.env`  
- ❌ Rsync patient `data/`  
- ❌ Hardcode DigitalOcean IPs or duckdns hostnames in YAML  
