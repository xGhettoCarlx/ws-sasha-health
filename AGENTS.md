# Sasha Health — Agent Context

> Location: `~/Station/mini_apps_studio/apps/sasha-health/`  
> Migrated from legacy OpenCode `WorkStation/Projects/Project5` (2026-07-17).  
> This file describes **reality as of v2.7.0**, not aspirational product decks.

## What this product is

**Telegram Mini App (TMA) + FastAPI medical vault for Sasha.**

Users open a WebApp at base path `/sh/`, authenticate via Telegram `initData`, and manage:

- Profile / diagnoses / allergies (`data/карточка.md`)
- Medications + stock alerts (`data/лекарства/`)
- Visits, labs, imaging (Hermes-style MD bundles)
- Insurance, fluorography, strategy, symptom diary
- Inbox: upload scan → optional Grok Vision OCR → verify

It is **not** a voice step-counter bot and does **not** use Supabase/PostgreSQL in the runtime path.

## Current stack (truth)

| Layer | Technology | Notes |
|-------|------------|--------|
| **Backend** | Python 3.12+, **FastAPI** | Entry: `app/main.py`, port 8000 |
| **Storage** | **MDStorage** — Markdown + YAML frontmatter | `app/storage.py`, root `data/` |
| **Auth** | Telegram Mini App initData (HMAC) + whitelist | `app/auth.py`; multi-bot path supported |
| **Bot** | aiogram 3.x | **Outbound notifications only** — no conversational webhook handlers |
| **OCR** | xAI Grok Vision (optional) | `app/ocr.py`; needs `XAI_API_KEY` |
| **Frontend** | **React 19 + TypeScript + Vite 6** | `frontend/src/`, SPA base `/sh/` |
| **UI** | Tailwind CSS 4, shadcn-style components, Zustand, TanStack Query, `@telegram-apps/sdk-react` | Version **2.7.0** (Apple Liquid Glass) |
| **Tests** | pytest (22 modules under `tests/`) | |
| **Deploy** | GitHub Actions `deploy-sasha-health.yml` (rsync SPA + optional API via `DO_*` secrets) | See `docs/GITHUB_ACTIONS_SECRETS_CHECKLIST.md` |

### Explicitly NOT the stack

- ❌ Vanilla JS SPA (old root `js/` / `css/` — left in legacy WorkStation, not migrated)
- ❌ Supabase / PostgreSQL as primary DB
- ❌ Voice metric tracking product from outdated Product.md
- ❌ OpenCode `.omo` session junk

## Architecture

```text
Telegram WebApp / PWA
  React 19 SPA  (frontend/src, base /sh/)
        │  Authorization: tma <initData>  or  X-User-ID (PWA)
        ▼
FastAPI  (app/main.py)
  routes: auth, admin, profile, pharmacy, history, schedule,
          insurance, fluorography, inbox, media
  bot.py   → outbound TG messages + Mini App button
  ocr.py   → Grok Vision → AnalysisSchema
  cron/    → medication & visit checks
        │
        ▼
MDStorage  (atomic write + fcntl flock)
  data/**  ← YAML frontmatter + markdown body  (= the database)
```

## Layout

```text
sasha-health/
├── app/                 # FastAPI package
│   ├── main.py
│   ├── auth.py
│   ├── config.py
│   ├── storage.py       # MDStorage
│   ├── bot.py
│   ├── ocr.py
│   ├── routes/
│   ├── schemas/         # Pydantic domain models
│   └── cron/
├── frontend/            # React 19 SPA (source of truth for UI)
│   ├── src/
│   ├── public/
│   └── package.json     # version 2.7.0
├── data/                # Medical records (CRITICAL — backup before edits)
├── tests/
├── scripts/
├── docs/                # history from migration + future ARCH/PRODUCT
├── LocalLibrary/        # Product/CONTEXT (keep truthful)
├── deploy.sh
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Commands

```bash
# Backend
cd ~/Station/mini_apps_studio/apps/sasha-health
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill BOT_TOKEN etc. — never commit .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm ci && npm run dev     # Vite :5173
npm run build                           # → frontend/dist

# Tests
pytest

# Local emergency SPA deploy (requires DO_HOST, DO_SSH_USER, DO_SPA_REMOTE_PATH)
# Prefer GitHub Actions in production.
bash deploy.sh
```


## Known debt (do not “rediscover”)

1. **Medicine IDs are index-based** (sort order in `лекарства/`) — unstable under insert/delete.
2. **Dual visit stores:** `data/schedule/` (`/api/schedule`) vs `data/Терапевт/` (`/api/history` visits).
3. **Zustand split:** `frontend/src/stores/*` and `features/*/store.ts`.
4. **Analytics full page** exists but is not registered in `routes.tsx`.
5. Backend deploy on VPS is less codified than frontend SCP.

Prefer fixing these over inventing a new stack.

## Secrets

- Use Station vault / `secrets_resolve` when available.
- Local: `.env` from `.env.example` only; **never commit** tokens.
- Legacy path (reference only): `WorkStation/GeneralLibrary/secrets/active/projects/Project5/`.

## Rules for agents

- ✅ Change backend and React source under this folder.
- ✅ Keep `data/*.md` frontmatter valid (`trust_tier`, `date` where required).
- ✅ After UI changes: `npm run build` must pass.
- ❌ Do not reintroduce vanilla JS UI.
- ❌ Do not add Supabase “because old docs said so” without an explicit product decision.
- ❌ Do not create OpenCode `.omo/run-continuation` noise here.
- ❌ Do not touch `~/Station/Workstation/` (capital W — agent-ops city).
