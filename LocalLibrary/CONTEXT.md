# Sasha Health — Architecture & Context (truthful)

> Updated: 2026-07-17 after migration into `mini_apps_studio`.  
> Supersedes the old OpenCode CONTEXT that incorrectly claimed Supabase + webhooks.

## Product summary

Personal **medical records Telegram Mini App** for Sasha: profile, medications, visits/labs, insurance, strategy, document inbox with optional OCR.

## Stack

| Layer | Implementation |
|-------|----------------|
| API | FastAPI (`app/main.py`) |
| Database | **None (SQL).** File store: Markdown + YAML frontmatter via `MDStorage` |
| Data dir | `data/` (Docker volume `./data:/app/data`, env `DATA_DIR`) |
| UI | **React 19 + TypeScript + Vite 6**, served under `/sh/` |
| Auth | Telegram WebApp `initData` HMAC (`telegram-init-data`); whitelist `ALLOWED_TELEGRAM_IDS` |
| Bot | aiogram 3 — **send notifications / Mini App button only** |
| OCR | Optional Grok Vision (`XAI_API_KEY`) for inbox uploads |
| Cron | `app/cron/check_medications.py`, `check_visits.py` |

## Architecture diagram

```text
Telegram Mini App (React 19 SPA @ /sh/)
        │  header: Authorization: tma <initData>
        ▼
   FastAPI :8000
        │
        ├── /api/*     JSON APIs (auth required except /health)
        ├── /sh/*      static SPA + client routes
        └── MDStorage → data/**/*.md
```

There is **no** PostgreSQL/Supabase in this runtime. Old docs that showed:

```text
Telegram ← webhook → FastAPI → PostgreSQL (Supabase)
```

are **obsolete and false** for this codebase.

## Data plane (`data/`)

| Path | Role |
|------|------|
| `карточка.md` | Patient profile, diagnoses, allergies |
| `стратегия.md` | Treatment / daily strategy |
| `страховка.md` | Insurance policies |
| `флюорография.md` | Fluorography history |
| `лекарства/*.md` | One file per medication |
| `schedule/*.md` | Planned visits (API `/api/schedule`) |
| `Терапевт/`, `Анализы/`, `УЗИ/`, `МРТ-КТ/` | Hermes-style exam/visit bundles |
| `дневник/`, `дневник_симптомов.md` | Quick notes / symptoms |
| `чекапы.md`, `household.md` | Checkups / household notes |

Trust tiers on records: `unverified` | `verified` | `trusted`.

## Integrations

| Service | Role | Config |
|---------|------|--------|
| Telegram Bot API | Outbound messages, WebApp button | `BOT_TOKEN`, `MINI_APP_URL` |
| Telegram WebApp | Client shell + initData auth | Frontend SDK |
| xAI Grok Vision | Optional medical document OCR | `XAI_API_KEY` |
| VPS nginx | Host SPA at `/var/www/sh/` | `deploy.sh` |

Secrets: prefer Station vault. Do not commit `.env`.

## Frontend routes (React Router)

| Path | Screen |
|------|--------|
| `/login` | Login / PWA auth |
| `/dashboard` | Home (insurance, daily, meds, quick BP, inbox) |
| `/records` | Records |
| `/medications` | Medications |
| `/history` | History / labs |
| `/profile` | Profile (+ modals: diagnoses, allergies, insurance, fluoro) |
| `/strategy` | Strategy |

## Known architectural issues

1. Pharmacy entity IDs = array index (fragile).
2. Visits split across `schedule/` and `Терапевт/`.
3. Frontend store layout inconsistent (global vs feature stores).

See root `AGENTS.md` and Station plan  
`Memory/ops_queue/WORKSTATION_MIGRATION_PLAN.md` §7 for refactor roadmap.

## Runtime

```bash
# API
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Health check (no auth): GET /health  → storage probe on DATA_DIR
```

## Related paths

| Path | Role |
|------|------|
| `~/Station/mini_apps_studio/` | Mini-App Production Department (this home) |
| `~/Station/Workstation/` | **Different** city — sasha-work / OpenCode playbooks (do not mix) |
| Legacy `~/WorkStation/Projects/Project5` | Source freeze after migration; do not dual-write |
