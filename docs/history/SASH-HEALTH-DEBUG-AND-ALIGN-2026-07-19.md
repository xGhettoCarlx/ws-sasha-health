# SASH-HEALTH-DEBUG-AND-ALIGN — 2026-07-19

## Diagnosis

- FastAPI + SPA under `/sh/` served 200 locally; core navigator APIs worked with admin `X-User-ID`.
- Production SPA build tree-shook browser local-auth (`import.meta.env.DEV`), so opening `/sh/` without Telegram dropped users on Login and did not auto-load agent files.
- Placeholder `BOT_TOKEN=dev-local-placeholder` was treated as a real token → unauthenticated API calls returned **401**.
- Agent lab YAML uses flags `✅` / `⚠️` / `🔴`; bridge only recognized `high|low|↑|↓` → **Pre-Visit `labs_used: 0`**.
- Medications, Records, Profile, History, Strategy pages still rendered **mock-data**, not `data/` dual-write files.
- Pharmacy files omit `is_daily`; Mg «на ночь / регулярно» was not treated as daily.
- Legacy `test_static` expected old `/css` `/js` layout (pre-React).

## Agent data flow (chat → files → API)

| Input (chat) | Agent write | Mini App path | API |
|---|---|---|---|
| АД / вес | diary frontmatter `bp`, `weight_kg` | `data/дневник/*.md` | `GET/POST /api/vitals`, overview |
| Жалобы | `entries[]` in YAML | `data/копилка_жалоб.md` | `/api/complaints` |
| Чекапы table | markdown table | `data/чекапы.md` | `/api/checkups` |
| Лекарства | per-file YAML | `data/лекарства/*.md` | `/api/pharmacy/` |
| Анализы | parameters + emoji flags | `data/Анализы/...` | previsit labs, history analytics |
| Визиты | schedule YAML | `data/schedule/*.md` | `/api/schedule/`, history visits |
| Карточка | ProfileSchema | `data/карточка.md` | `/api/profile/` |

Hermes working notes stay in `~/Hermes/Саша/Боты/sasha-health/`; Mini App consumes **structured** dual-write under `mini_apps_studio/apps/sasha-health/data/`.

## Fixes

1. `app/auth.py` — placeholder tokens → dev mode; no-auth mock user when no real bot token.
2. `app/routes/navigator_api.py` — emoji abnormal flags; BP/weight coercion from free-text diary.
3. `app/routes/pharmacy.py` — infer `is_daily`, expose `stock_count`.
4. Frontend: local owner auth `80101636` unless `VITE_LOCAL_AUTH=false`; Login opens real data.
5. Wire Medications / Records / Profile / History / Strategy to live APIs.
6. `tests/test_static.py` aligned with `/sh` SPA.
7. `npm run build` → `frontend/dist` (gitignored; CI builds).

## Verification (local)

- `/sh/` 200; hashed assets 200
- Unauthenticated (dev): overview, vitals, checkups, complaints, navigator, pharmacy, profile, strategy, schedule, analytics **200**
- Previsit: `labs_used=4`, `complaints_used=2`
- Abnormal labs: Холестерин общий, Триглицериды, Билирубин общий, АлАТ
- Pharmacy: Магний `is_daily=true`
- pytest: auth + main + static **34 passed**

## Research notes (no reinvent)

- Personal health Mini Apps: keep **chat as capture**, Mini App as **read/action** (vitals quick log, checkups, visit prep) — matches agent dual-write pattern already in skill.
- Healthcare UI: prioritize simple dashboard of active vitals + due items; med trackers with stock; pre-visit summaries for clinicians.
- Telegram Mini App UX: native MainButton for primary actions, bridge chat↔app via notifications; our BottomNav + Pre-Visit copy-prompt fits Zero-API Gemini path.
- Repo `xGhettoCarlx/ws-sasha-health` is the single app package (no second medical Mini App reference implementation in-tree); patterns taken from Hermes skill dual-write + existing FastAPI routers.

## Remaining risks

- Production with **real** `BOT_TOKEN` still requires Telegram initData or whitelist/`X-User-ID` (dev open-auth only for placeholders).
- Dual-write lag: agent may update Боты/ without Mini App `data/` — SPA will look stale until dual-write runs.
- Strategy YAML `steps[]` empty; UI parses markdown body (fragile if format changes).
- History ALT chart needs multiple dated points for a real trend.
