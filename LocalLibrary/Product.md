# Sasha Health — Product Description (truthful)

> Updated: 2026-07-19. Real-data medical navigator rework (no fake SpO₂/pulse/temp trackers).

## Purpose

Personal **medical navigator** delivered as a **Telegram Mini App / PWA** for Sasha:

- **Vitals:** blood pressure (1–2×/day) and weight only — no pulse/SpO₂/temperature demos.
- **Checkups:** yearly/half-year procedures from `чекапы.md` with due status.
- **Complaints bank:** accumulate symptoms until the next doctor visit.
- **Navigator + insurance:** symptoms/labs → specialty → DМС coverage (Белгосстрах).
- **Pre-Visit (Zero-API):** assemble a Gemini prompt from card + complaints + abnormal labs (copy button, no PDF).
- Vault for diagnoses, meds, visits, labs, imaging, strategy (existing MD files).

## Users

- **Sasha** — primary patient/operator (whitelist auth).
- Admin approve flow for new Telegram IDs (`/api/admin`).
- `household.md` exists as a seed for multi-person notes; full multi-tenant is **not** productized yet.

## Features (implemented)

- [x] Telegram Mini App UI (React 19 SPA, base `/sh/`)
- [x] Profile / diagnoses / allergies
- [x] Medications CRUD + stock adjust + alerts
- [x] History / analytics over MD exam bundles
- [x] Schedule visits (note: parallel store to therapist visits — tech debt)
- [x] Insurance & fluorography views
- [x] Strategy document view
- [x] Symptom diary + quick records
- [x] Inbox upload + optional Grok Vision OCR + verify/reject
- [x] PWA-oriented auth path + TMA initData
- [x] Cron scripts for meds / visits notifications

## Features (not this product)

- Voice message → metrics pipeline (steps/sleep/water…) — **not implemented**; old roadmap only
- PostgreSQL / Supabase primary storage — **not used**
- Full conversational health chatbot with webhooks — bot is notify-only

## Tech (summary)

| Piece | Choice |
|-------|--------|
| Backend | FastAPI |
| Persistence | MDStorage (Markdown + YAML frontmatter files) |
| Frontend | React 19 + Vite 6 + TypeScript + Tailwind 4 |
| Telegram | Mini App + aiogram notifications |
| Optional AI | xAI Grok Vision OCR |

## Status

- Frontend package version: **2.7.0**
- Migrated home: `~/Station/mini_apps_studio/apps/sasha-health/`
- Next engineering: stable medicine IDs, unify visit stores (see migration plan §7)
