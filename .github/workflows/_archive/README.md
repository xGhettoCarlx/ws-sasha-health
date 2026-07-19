# Archived legacy workflows

These files are **historical only** — GitHub Actions ignores `_archive/` if it is not a standard workflow path…  
**Important:** workflows must live directly under `.github/workflows/*.yml`. Files in this folder are documentation copies and will not run.

| File | Origin | What it did (legacy) |
|------|--------|----------------------|
| `deploy.legacy-project5.yml` | `Projects/Project5/.github/workflows/deploy.yml` | SCP **raw** project tree (often unbuilt) to `/var/www/sasha-health` using `SSH_*` secrets |
| `deploy-sasha-health.legacy-workstation-monorepo.yml` | `WorkStation/.github/workflows/deploy-sasha-health.yml` | SCP `Projects/Project5/frontend/*` **without** `npm run build` |

## Why replaced

1. No Node build step — React 19 SPA never produced `dist/` in CI.  
2. Hard-coded remote absolute paths in YAML (`/var/www/...`).  
3. No backend package / pytest gate.  
4. Legacy `deploy.sh` defaulted to a fixed VPS hostname (removed in local script).

**Active pipeline:** `../deploy-sasha-health.yml`
