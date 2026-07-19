# project5-react-migration — Work Plan

## TL;DR (For humans)

**What you'll get:** Полная миграция фронтенда Sasha Health с vanilla JS на React 19 + TypeScript + shadcn/ui + PWA. Сохраняется весь бэкенд (FastAPI, 8 роутеров, multi-bot auth), все 7 страниц приложения пересоздаются как React-компоненты с Zustand-стейтом, React Router-роутингом и Tailwind-стилями. Приложение устанавливается на Android/iOS как PWA с отдельным режимом аутентификации (stored token).

**Why this approach:** Миграция идёт feature-by-feature, каждая страница — независимый модуль с собственным API-хуком и Zustand-слайсом. Бэкенд не трогаем (кроме одного нового эндпоинта /api/auth/pwa). Типы генерируются из Pydantic-схем вручную (один раз, Wave 2), затем все страницы пишутся параллельно. Шаблон — `patterns/mini-app-template/` (React 19 + shadcn/ui + TelegramUI + Zustand).

**What it will NOT do:**
- НЕ меняет бэкенд (кроме добавления POST /api/auth/pwa)
- НЕ меняет формат данных в `data/*.md`
- НЕ добавляет новые фичи — только перенос существующей логики на React

**Effort:** XL (6 waves, ~30 tasks, ~7 feature pages)
**Risk:** Medium — бэкенд стабилен, основная сложность в точном воспроизведении бизнес-логики каждого модуля
**Decisions to sanity-check:**
  1. Insurance и FLG убраны из BottomNav (7→5 табов), доступны через Profile как sub-route — как в плане project5-refactor.md
  2. PWA auth: храним токен в localStorage, бэкенд проверяет его через новый эндпоинт
  3. CSS: полная замена 2156 строк app.css на Tailwind + shadcn/ui (без переноса CSS, только логика)

Your next move: approve — or run high-accuracy review via `$review`. Full execution detail follows below.

---

> TL;DR (machine): XL effort, Medium risk — React 19 + TS + shadcn migration of 7 pages, 11 API endpoints, 5 infrastructure modules, PWA support, backend unchanged except 1 new endpoint.

## Scope

### Must have
- [x] React 19 + TypeScript + Vite 6 setup (замена Vite 8 на 6 из шаблона)
- [x] shadcn/ui + TelegramUI компоненты
- [x] Tailwind CSS 3.4 (полная замена 2156 строк app.css)
- [x] Zustand 5 stores (auth, each feature slice)
- [x] React Router 7 (lazy routes)
- [x] @telegram-apps/sdk-react (Telegram SDK integration)
- [x] Все 7 страниц: records, medications, analytics, history, profile, insurance, fluorography
- [x] BottomNav c 5 табами (insurance и FLG — sub-routes в Profile)
- [x] API client с auth-заголовком (Authorization: tma <initData>)
- [x] PWA: manifest.json, Service Worker (vite-plugin-pwa), иконки 192/512px
- [x] PWA auth: POST /api/auth/pwa (stored token)
- [x] Telegram theme (светлая/тёмная тема через CSS variables)
- [x] framer-motion анимации переходов между страницами
- [x] Lucide React иконки (замена emoji-иконок в BottomNav)
- [x] version.json cache busting
- [x] Vite build → `frontend/dist/` с `base: '/sh/'`
- [x] Все 11 API endpoints работают идентично текущему поведению
- [x] Multi-bot auth и 403 pending_approval обрабатываются

### Must NOT have (guardrails, anti-slop, scope boundaries)
- ❌ НЕ трогать бэкенд (`app/`) кроме добавления одного роута `POST /api/auth/pwa`
- ❌ НЕ менять формат `data/*.md` файлов
- ❌ НЕ добавлять новые фичи, не существующие в vanilla JS версии
- ❌ НЕ использовать `any`, `@ts-ignore`, `as` для подавления типов
- ❌ НЕ писать самописный CSS — только Tailwind utility classes + shadcn/ui variants
- ❌ НЕ создавать файлы >250 LOC (максимум 250 строк для любого файла)
- ❌ НЕ оставлять мёртвый код: BMR калькулятор (CSS есть, JS нет) — НЕ переносить
- ❌ НЕ менять `ALLOWED_TELEGRAM_IDS` логику и whitelist
- ❌ НЕ хардкодить BOT_TOKEN
- ❌ НЕ удалять старый фронтенд до верификации нового (Wave 6)

## Verification strategy
> Zero human intervention — all verification is agent-executed.
- Test decision: tests-after (vitest + @testing-library/react для ключевых хуков и компонентов)
- Evidence: .omo/evidence/task-<N>-project5-react-migration.<ext>
- Build verification: `npm run build` должен проходить без ошибок для каждого wave
- TypeScript: `tsc --noEmit` strict mode без ошибок
- LSP diagnostics: чистые на всех изменённых файлах
- API smoke test: curl каждый эндпоинт после деплоя

## Execution strategy

### Parallel execution waves
Wave 1 (6 tasks) → Wave 2 (6 tasks) → Wave 3 (4 tasks) → Wave 4 (3 tasks) → Wave 5 (7 tasks, ALL parallel) → Wave 6 (5 tasks)

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1.1 Init Vite project | — | 1.2-1.5, все последующие | — |
| 1.2 Dependencies | 1.1 | 1.3, 1.5 | 1.4 |
| 1.3 Tailwind + shadcn | 1.2 | 4.1-4.3, 5.1-5.7 | 1.4, 1.5 |
| 1.4 PWA config | 1.2 | 3.1, 3.2 | 1.3, 1.5 |
| 1.5 Directory structure | 1.1 | все feature pages | 1.3, 1.4 |
| 1.6 TypeScript config | 1.1 | все .ts/.tsx файлы | 1.3-1.5 |
| 2.1 TypeScript types | 1.1 | 2.2, 5.1-5.7 | 2.3-2.6 |
| 2.2 API client | 2.1 | 5.1-5.7 | 2.3-2.6 |
| 2.3 Auth store | — | 2.6, 3.4, 4.2 | 2.2, 2.4, 2.5 |
| 2.4 Theme hook | — | 2.6, 4.1 | 2.2, 2.3, 2.5 |
| 2.5 Providers | 2.3, 2.4 | 4.2, все страницы | 2.6 |
| 2.6 AppShell | 2.3, 2.4, 2.5 | 4.1, 4.2 | — |
| 3.1 manifest + icons | 1.4 | 3.2 | 3.3, 3.4 |
| 3.2 Service Worker | 3.1 | — | 3.3, 3.4 |
| 3.3 Backend PWA auth | — | 3.4 | 3.1, 3.2 |
| 3.4 Auth gate | 2.3, 3.3 | 4.2 | — |
| 4.1 BottomNav | 2.6 | 4.2 | 4.3 |
| 4.2 Router setup | 2.5, 2.6, 3.4, 4.1 | все страницы | — |
| 4.3 PageShell | — | 5.1-5.7 | 4.1 |
| 5.1 RecordsPage | 2.1, 2.2, 4.2 | — | 5.2-5.7 |
| 5.2 MedicationsPage | 2.1, 2.2, 4.2 | — | 5.1, 5.3-5.7 |
| 5.3 AnalyticsPage | 2.1, 2.2, 4.2 | — | 5.1-5.2, 5.4-5.7 |
| 5.4 HistoryPage | 2.1, 2.2, 4.2 | — | 5.1-5.3, 5.5-5.7 |
| 5.5 ProfilePage | 2.1, 2.2, 4.2 | — | 5.1-5.4, 5.6-5.7 |
| 5.6 InsurancePage | 2.1, 2.2, 4.2 | — | 5.1-5.5, 5.7 |
| 5.7 FluorographyPage | 2.1, 2.2, 4.2 | — | 5.1-5.6 |
| 6.1 Animations | — | — | 6.2-6.5 |
| 6.2 Theme toggle | — | — | 6.1, 6.3-6.5 |
| 6.3 Cache busting | — | — | 6.1-6.2, 6.4-6.5 |
| 6.4 Vite build config | — | 6.5 | 6.1-6.3 |
| 6.5 Deploy + cleanup | 6.4 | — | 6.1-6.3 |

## Todos

### WAVE 1: Project Initialization

- [ ] 1.1. frontend/: Initialize Vite + React + TypeScript project with all dependencies
  What to do: Run `npm create vite@latest` with React+TS template in a temp dir, then merge into existing frontend/. Install ALL dependencies from patterns/mini-app-template/package.json PLUS additional: framer-motion, vite-plugin-pwa, @tanstack/react-query.
  Must NOT do: Do NOT delete existing vanilla JS files yet — they will be cleaned up in Wave 6. Do NOT touch backend files.
  Parallelization: Wave 1 | Blocked by: — | Blocks: 1.2-1.5, all subsequent waves
  References: patterns/mini-app-template/package.json:1-31, frontend/package.json:1-14
  Acceptance criteria: `npm ls react@19 react-dom@19 typescript@5 vite@6` shows correct versions. `npm run dev` starts Vite dev server.
  QA scenarios: Run `npm install && npm run dev` — dev server starts on port 5173. Run `npm run build` — builds without errors. Evidence: .omo/evidence/task-1.1-project5-react-migration.txt
  Commit: Y | chore(frontend): init Vite + React + TypeScript project with all dependencies

- [ ] 1.2. frontend/: Configure Tailwind CSS 3.4 + PostCSS + shadcn/ui init
  What to do: Create tailwind.config.js with Telegram theme CSS variables mapped to Tailwind theme. Run `npx shadcn@latest init` (defaults: TypeScript, CSS variables, base color zinc). Configure content paths to scan src/**/*.{ts,tsx}.
  Must NOT do: Do NOT use Tailwind v4 (use 3.4 to match template). Do NOT configure shadcn with New York style — use Default.
  Parallelization: Wave 1 | Blocked by: 1.1 | Blocks: 1.3 | Can parallelize with: 1.4, 1.5, 1.6
  References: patterns/mini-app-template/package.json:24-28 (tailwind + postcss + autoprefixer versions), patterns/mini-app-template/README.md:99-105 (Telegram CSS variables)
  Acceptance criteria: `npx tailwindcss --help` works. `components.json` exists with shadcn/ui config. `src/styles/globals.css` has @tailwind directives.
  QA scenarios: Create a test component with `className="bg-[var(--tg-theme-bg-color)] text-[var(--tg-theme-text-color)]"` — renders with CSS vars. Evidence: .omo/evidence/task-1.2-project5-react-migration.txt
  Commit: Y | chore(frontend): configure Tailwind CSS 3.4 + PostCSS + shadcn/ui

- [ ] 1.3. frontend/: Add shadcn/ui base components (button, card, input, sheet, skeleton, alert, badge, progress, tabs, separator)
  What to do: Run `npx shadcn@latest add` for each component: button, card, input, label, sheet, skeleton, alert, badge, progress, tabs, separator, dialog. These are the building blocks for all 7 feature pages.
  Must NOT do: Do NOT add components that aren't used (avoid unused shadcn components). Do NOT customize components beyond default — variants will be added in feature pages.
  Parallelization: Wave 1 | Blocked by: 1.2 | Blocks: 4.1, 4.3, 5.1-5.7 | Can parallelize with: 1.4, 1.5, 1.6
  References: patterns/mini-app-template/README.md:12 (shadcn/ui + TelegramUI), frontend/css/app.css:233-366 (settings-group/settings-row patterns → shadcn Card)
  Acceptance criteria: All 11 components present in `src/components/ui/`. `components.json` lists all aliases.
  QA scenarios: Import Button, Card, Sheet, Skeleton in a test page — all render without errors. Evidence: .omo/evidence/task-1.3-project5-react-migration.txt
  Commit: Y | feat(frontend): add shadcn/ui base components (11 components)

- [ ] 1.4. frontend/: Configure vite-plugin-pwa for PWA support
  What to do: Add vite-plugin-pwa to vite.config.ts with VitePWA plugin config: registerType 'autoUpdate', manifest with name 'Медицинский дневник', short_name 'Sasha Health', theme_color from Telegram bg, icons (192x192 + 512x512 PNG). Include workbox globPatterns for precaching.
  Must NOT do: Do NOT generate actual icon files yet (done in 3.1). Do NOT set injectRegister to 'inline' — use 'auto'.
  Parallelization: Wave 1 | Blocked by: 1.1 | Blocks: 3.1, 3.2 | Can parallelize with: 1.2, 1.3, 1.5, 1.6
  References: patterns/mini-app-template/README.md:99-105 (Telegram theme colors for manifest), frontend/vite.config.js:1-14 (existing Vite config — base: '/sh/')
  Acceptance criteria: `vite.config.ts` has VitePWA plugin with manifest and workbox config. `npm run build` generates `dist/sw.js` and `dist/manifest.webmanifest`.
  QA scenarios: Run `npm run build` — check dist/ for sw.js, workbox-*.js, manifest.webmanifest. Evidence: .omo/evidence/task-1.4-project5-react-migration.txt
  Commit: Y | feat(frontend): configure vite-plugin-pwa for PWA support

- [ ] 1.5. frontend/src/: Create directory structure following patterns/mini-app-template
  What to do: Create all directories: src/app/, src/features/{records,medications,analytics,history,profile,insurance,fluorography}/{api,components,store.ts}, src/components/ui/ (already populated by shadcn), src/hooks/, src/lib/, src/styles/. Create placeholder files: src/app/routes.tsx, src/lib/api.ts, src/lib/utils.ts.
  Must NOT do: Do NOT create files with actual logic — only directory structure and empty/placeholder exports. Do NOT delete existing frontend/js/ or frontend/css/.
  Parallelization: Wave 1 | Blocked by: 1.1 | Blocks: все feature page задачи | Can parallelize with: 1.2, 1.3, 1.4, 1.6
  References: patterns/mini-app-template/README.md:19-46 (directory structure), frontend/main.js:1-31 (import order maps to dependency graph)
  Acceptance criteria: All 7 feature directories exist with api/, components/, store.ts sub-structure. src/app/ has routes.tsx placeholder. src/hooks/ and src/lib/ exist.
  QA scenarios: `ls src/features/*/store.ts` returns 7 files. `ls src/components/ui/` shows shadcn components. Evidence: .omo/evidence/task-1.5-project5-react-migration.txt
  Commit: Y | chore(frontend): create directory structure for React migration

- [ ] 1.6. frontend/: Set up TypeScript strict config + path aliases
  What to do: Configure tsconfig.json with strict: true, noUncheckedIndexedAccess: true, exactOptionalPropertyTypes: false. Add path aliases: @/ → src/, @components/ → src/components/, @features/ → src/features/, @hooks/ → src/hooks/, @lib/ → src/lib/. Configure vite.config.ts resolve.alias to match.
  Must NOT do: Do NOT set strict: false. Do NOT use paths without corresponding vite aliases.
  Parallelization: Wave 1 | Blocked by: 1.1 | Blocks: все .ts/.tsx файлы | Can parallelize with: 1.2, 1.3, 1.4, 1.5
  References: patterns/mini-app-template/package.json:22-23 (@types/react, @types/react-dom), patterns/mini-app-template/README.md:19-46 (path structure)
  Acceptance criteria: `tsc --noEmit` passes on empty project. Import from `@/lib/utils` resolves correctly in Vite.
  QA scenarios: Create a test file with `import { cn } from '@/lib/utils'` — `tsc --noEmit` and Vite resolve it. Evidence: .omo/evidence/task-1.6-project5-react-migration.txt
  Commit: Y | chore(frontend): configure TypeScript strict mode + path aliases

### WAVE 2: Foundation Layer

- [ ] 2.1. src/lib/types.ts: Define TypeScript interfaces matching all Pydantic schemas
  What to do: Create TypeScript types/interfaces mirroring ALL Pydantic models from app/schemas/. Include: CommonBase (id, trust_tier, tags, date, source, content), TrustTier, DiagnosisItem, ProfileSchema, StrategyStep, StrategySchema, VisitItem, VisitStatus, VisitSchema, DiagnosticFinding, MedicineSchema, InsurancePolicy, InsuranceSchema, FluorographyRecord, FluorographySchema, SymptomEntry, SymptomDiarySchema, AnalysisSchema, ParameterItem, InboxItemSchema, OcrStatus, ScheduleSchema.
  Must NOT do: Do NOT use `any`. Do NOT skip optional fields — use `?:` for Optional[str] fields. Do NOT add fields not present in Pydantic models.
  Parallelization: Wave 2 | Blocked by: 1.1 | Blocks: 2.2, 5.1-5.7 | Can parallelize with: 2.3, 2.4, 2.5, 2.6
  References: app/schemas/__init__.py:1-56 (all exports), app/schemas/common.py:1-44 (CommonBase, TrustTier), app/schemas/profile.py:1-42 (ProfileSchema, DiagnosisItem), app/schemas/strategy.py:1-53 (StrategySchema, StrategyStep), app/schemas/medicine.py:1-32 (MedicineSchema), app/schemas/insurance.py:1-44 (InsuranceSchema, InsurancePolicy), app/schemas/fluorography.py:1-32 (FluorographySchema, FluorographyRecord), app/schemas/symptoms.py:1-36 (SymptomEntry, SymptomDiarySchema), app/schemas/analysis.py:1-59 (AnalysisSchema, ParameterItem), app/schemas/visit.py:1-62 (VisitSchema, DiagnosticFinding), app/schemas/schedule.py:1-59 (ScheduleSchema, VisitItem, VisitStatus), app/schemas/inbox.py:1-45 (InboxItemSchema, OcrStatus)
  Acceptance criteria: `tsc --noEmit` passes. All Pydantic model fields have TypeScript equivalents with correct types (str→string, Optional[str]→string|undefined, list[X]→X[], Literal[...]→union type).
  QA scenarios: Create a variable `const p: ProfileSchema = { full_name: "test", birth_date: "2000-01-01", trust_tier: "verified", date: "2026-01-01" }` — typechecks without errors. Evidence: .omo/evidence/task-2.1-project5-react-migration.txt
  Commit: Y | feat(frontend): define TypeScript types for all Pydantic schemas

- [ ] 2.2. src/lib/api.ts: Create typed API client with auth headers
  What to do: Replace frontend/api.js with a typed fetch wrapper. Create `apiFetch<T>(path, options?)` that adds `Authorization: tma <initData>` header (from Zustand auth store or Telegram WebApp SDK). Include error handling: ApiError class with status+body, network error detection. Export typed methods for all 11 endpoints: getRecords, getMedications, addMedication, getAnalytics, getCategories, getVisits, getProfile, updateProfile, getStrategy, getSymptoms, addSymptom, getInsurance, getFluorography.
  Must NOT do: Do NOT use `any` return types — every method returns a typed Promise<T>. Do NOT import from window.* globals — use Zustand store.
  Parallelization: Wave 2 | Blocked by: 2.1 | Blocks: 5.1-5.7 | Can parallelize with: 2.3, 2.4, 2.5, 2.6
  References: frontend/api.js:1-295 (ALL current API logic — authHeader at line 15, apiFetch at line 20, all endpoint methods), patterns/mini-app-template/README.md:83-95 (API client pattern), app/auth.py:172-201 (_extract_initData — 3 auth modes: header tma, X-Telegram-InitData, query param)
  Acceptance criteria: All 11 endpoint methods exist with typed signatures. `apiFetch` throws ApiError on non-OK responses. Auth header includes `tma ` prefix.
  QA scenarios: Mock fetch to return 200 + JSON → verify typed response. Mock fetch to return 403 pending_approval → verify ApiError thrown with status 403. Evidence: .omo/evidence/task-2.2-project5-react-migration.txt
  Commit: Y | feat(frontend): create typed API client with auth headers

- [ ] 2.3. src/hooks/useAuth.ts + src/lib/auth-store.ts: Create auth Zustand store
  What to do: Create Zustand store with: initData (string|null), user (TelegramUser|null), isVerified (boolean), isPending (boolean), isPwa (boolean). Provide actions: setInitData(initData), setUser(user), logout(). Create useAuth hook that reads Telegram WebApp.initData on mount (if in Telegram), or reads stored PWA token from localStorage. Handle pending_approval (403) state.
  Must NOT do: Do NOT access window.Telegram without null check. Do NOT store initData in localStorage — only PWA token.
  Parallelization: Wave 2 | Blocked by: — | Blocks: 2.5, 2.6, 3.4, 4.2 | Can parallelize with: 2.1, 2.2, 2.4
  References: app/auth.py:70-166 (verify_telegram_auth — verified/unverified + multi-bot), app/auth.py:204-235 (verify_telegram_auth_from_request — 403 pending_approval), frontend/api.js:15-18 (authHeader using window.Telegram.WebApp.initData), frontend/js/records.js:518-534 (showPendingApproval)
  Acceptance criteria: Store initializes with null initData. Calling setInitData updates state. useAuth hook returns { user, isVerified, isPending, isPwa }. PWA token persisted to localStorage.
  QA scenarios: Create a test component using useAuth() — renders user name when authenticated, shows pending screen when isPending. Evidence: .omo/evidence/task-2.3-project5-react-migration.txt
  Commit: Y | feat(frontend): create auth Zustand store + useAuth hook

- [ ] 2.4. src/hooks/useTelegramTheme.ts: Create Telegram theme hook
  What to do: Create hook that reads Telegram WebApp themeParams (bg_color, text_color, hint_color, button_color, button_text_color, secondary_bg_color, link_color) and sets them as CSS custom properties on :root. Also reads colorScheme (light/dark) and applies appropriate Tailwind dark class. Listen for themeChanged event.
  Must NOT do: Do NOT hardcode colors — always read from tg.themeParams. Do NOT call tg.ready()/tg.expand() here — that's done in Providers/AppShell.
  Parallelization: Wave 2 | Blocked by: — | Blocks: 2.5, 2.6, 4.1 | Can parallelize with: 2.1, 2.2, 2.3
  References: patterns/mini-app-template/README.md:99-105 (Telegram CSS variables pattern), frontend/app-shell.js:1-185 (Telegram theme init — tg.ready, tg.expand, themeParams application), frontend/css/app.css:17-49 (CSS custom properties with fallbacks)
  Acceptance criteria: Hook sets --tg-theme-bg-color, --tg-theme-text-color, --tg-theme-hint-color, --tg-theme-button-color, --tg-theme-secondary-bg-color, --tg-theme-link-color on document.documentElement. Responds to themeChanged event.
  QA scenarios: Mock window.Telegram.WebApp.themeParams with test colors → verify CSS vars set. Change colorScheme → verify dark class toggled. Evidence: .omo/evidence/task-2.4-project5-react-migration.txt
  Commit: Y | feat(frontend): create useTelegramTheme hook with CSS variable binding

- [ ] 2.5. src/app/Providers.tsx: Create root providers wrapper
  What to do: Create Providers component wrapping: SDKProvider (@telegram-apps/sdk-react) → QueryClientProvider (@tanstack/react-query) → BrowserRouter (react-router-dom) → ThemeProvider (applies Telegram theme) → children. Initialize Telegram SDK (useTelegramTheme inside).
  Must NOT do: Do NOT put business logic in Providers — only provider wrapping. Do NOT use multiple QueryClient instances — one shared.
  Parallelization: Wave 2 | Blocked by: 2.3, 2.4 | Blocks: 4.2, все страницы | Can parallelize with: 2.2, 2.6
  References: patterns/mini-app-template/README.md:50-64 (SDKProvider + ThemeProvider pattern), patterns/mini-app-template/package.json:13-20 (dependencies: @telegram-apps/sdk-react, react-router-dom, zustand)
  Acceptance criteria: Providers component wraps children with 4 providers. SDKProvider initializes without errors. QueryClientProvider configured with default options (staleTime: 30s, retry: 1).
  QA scenarios: Render `<Providers><div>test</div></Providers>` — no errors, providers applied in correct order. Evidence: .omo/evidence/task-2.5-project5-react-migration.txt
  Commit: Y | feat(frontend): create root Providers wrapper (SDK + Query + Router + Theme)

- [ ] 2.6. src/app/AppShell.tsx: Create root layout with safe-area
  What to do: Create AppShell component: `<div className="flex flex-col h-screen max-w-[500px] mx-auto overflow-hidden">` with safe-area padding (env(safe-area-inset-top), env(safe-area-inset-bottom)). Content area: `<main className="flex-1 overflow-y-auto">` with `<Outlet />` from react-router-dom.
  Must NOT do: Do NOT include BottomNav inside AppShell — BottomNav is a sibling component in the layout route. Do NOT use fixed positioning for the shell — use flex layout.
  Parallelization: Wave 2 | Blocked by: 2.3, 2.4, 2.5 | Blocks: 4.1, 4.2 | Can parallelize with: —
  References: patterns/mini-app-template/README.md:66-80 (AppShell with BottomNav pattern), frontend/app-shell.js:1-185 (current AppShell DOM creation), frontend/css/app.css:51-68 (current AppShell CSS — flex column, 100vh, max-width 500px)
  Acceptance criteria: AppShell renders flex column layout. Content area has overflow-y: auto. Safe-area insets applied. `<Outlet />` renders child routes.
  QA scenarios: Render AppShell with a test child route — child content scrolls within flex container, max-width respected. Evidence: .omo/evidence/task-2.6-project5-react-migration.txt
  Commit: Y | feat(frontend): create AppShell layout with safe-area + flex column

### WAVE 3: PWA + Authentication

- [ ] 3.1. frontend/public/: Create PWA manifest.json + app icons (192x192, 512x512)
  What to do: Create manifest.json with name "Медицинский дневник", short_name "Sasha Health", start_url "/sh/", display "standalone", theme_color "#ffffff" (with dark fallback), background_color "#ffffff". Create two PNG icons (192x192, 512x512) — simple medical cross or heart icon on colored background. Place in frontend/public/.
  Must NOT do: Do NOT use emoji as icon. Do NOT hardcode absolute URLs — use relative paths.
  Parallelization: Wave 3 | Blocked by: 1.4 | Blocks: 3.2 | Can parallelize with: 3.3, 3.4
  References: patterns/mini-app-template/README.md:99-105 (Telegram theme colors for manifest), frontend/index.html:1-47 (current meta tags — viewport, charset, cache-control)
  Acceptance criteria: manifest.json has all required fields (name, short_name, start_url, display, icons array). Both PNG files exist and are valid. `npm run build` includes both in dist/.
  QA scenarios: Open manifest.json — validates as JSON. `file` command on icons — actual PNG files. Evidence: .omo/evidence/task-3.1-project5-react-migration.txt
  Commit: Y | feat(frontend): add PWA manifest + app icons (192px, 512px)

- [ ] 3.2. frontend/src/: Register Service Worker with vite-plugin-pwa
  What to do: Configure vite-plugin-pwa workbox strategies: NetworkFirst for API calls, CacheFirst for static assets, StaleWhileRevalidate for HTML. Add `registerSW` from virtual:pwa-register in main.tsx entry point. Handle update prompt (show toast when new version available).
  Must NOT do: Do NOT cache API responses containing auth tokens. Do NOT use CacheFirst for /api/ endpoints.
  Parallelization: Wave 3 | Blocked by: 3.1 | Blocks: — | Can parallelize with: 3.3, 3.4
  References: frontend/index.html:14-34 (current cache-busting via version.json — keep this pattern for SW updates), frontend/vite.config.js:1-14 (base: '/sh/')
  Acceptance criteria: `npm run build` generates dist/sw.js and dist/workbox-*.js. Service Worker registered on page load. Update prompt appears when new SW version detected.
  QA scenarios: Build and serve — open DevTools → Application → Service Workers: SW registered. Reload without changes → SW unchanged. Change code, rebuild, reload → update prompt. Evidence: .omo/evidence/task-3.2-project5-react-migration.txt
  Commit: Y | feat(frontend): register Service Worker with auto-update

- [ ] 3.3. app/routes/pwa_auth.py: Create backend POST /api/auth/pwa endpoint
  What to do: Create new route file app/routes/pwa_auth.py. Implement POST /api/auth/pwa that accepts { initData: string }, validates it via app.auth.verify_telegram_auth(), and returns { token: string } (JWT or signed token with user_id + expiry). Token stored in localStorage by frontend, sent as Authorization: Bearer <token> header for subsequent requests. In app/main.py, mount the router and add Bearer token extraction to _extract_init_data() or create separate dependency.
  Must NOT do: Do NOT modify existing auth flow (Authorization: tma <initData> must still work). Do NOT use weak JWT secrets — derive from BOT_TOKEN. Do NOT change whitelist logic.
  Parallelization: Wave 3 | Blocked by: — | Blocks: 3.4 | Can parallelize with: 3.1, 3.2
  References: app/auth.py:1-235 (full auth flow — verify_telegram_auth, require_auth, extraction), app/main.py:1-113 (router mounting pattern), app/config.py:1-87 (Settings — BOT_TOKEN for signing), app/routes/pharmacy.py:1-255 (router pattern to follow)
  Acceptance criteria: POST /api/auth/pwa with valid initData returns { token: "..." }. Token can be verified on subsequent requests (GET /api/me with Bearer header). Invalid initData returns 401. Token has expiry (24h).
  QA scenarios: curl POST /api/auth/pwa with valid initData → 200 + token. curl GET /api/me with Bearer token → 200 + user. curl with expired token → 401. Evidence: .omo/evidence/task-3.3-project5-react-migration.txt
  Commit: Y | feat(backend): add POST /api/auth/pwa for standalone PWA auth

- [ ] 3.4. src/app/AuthGate.tsx: Create auth gate component
  What to do: Create AuthGate wrapper that: 1) Shows loading skeleton while checking auth. 2) If in Telegram → extracts initData from WebApp SDK, calls /api/me to validate. 3) If PWA → reads token from localStorage, calls /api/me with Bearer header. 4) On 403 pending_approval → shows pending screen with user_id. 5) On 401 → shows "Authentication required" error. 6) On success → renders children.
  Must NOT do: Do NOT render children before auth check completes. Do NOT redirect on auth failure — show inline error with retry. Do NOT call /api/me more than once on mount.
  Parallelization: Wave 3 | Blocked by: 2.3, 3.3 | Blocks: 4.2 | Can parallelize with: —
  References: frontend/js/records.js:518-534 (showPendingApproval — pending screen with Telegram user ID), app/auth.py:204-235 (require_auth — 401/403 responses), frontend/api.js:15-18 (authHeader pattern)
  Acceptance criteria: Loading skeleton shows while checking. Authenticated → children render. 403 → pending approval screen with user_id. 401 → error with retry. PWA flow: reads token from localStorage, sends Bearer header.
  QA scenarios: Mock /api/me 200 → children render. Mock 403 → pending screen. Mock 401 → error screen with retry button. Evidence: .omo/evidence/task-3.4-project5-react-migration.txt
  Commit: Y | feat(frontend): create AuthGate component with loading/error/pending states

### WAVE 4: Layout + Navigation

- [ ] 4.1. src/components/BottomNav.tsx: Create BottomNav component with 5 tabs
  What to do: Create BottomNav component: fixed bottom bar with safe-area-inset-bottom padding. 5 tabs: Записи (ClipboardList), Препараты (Pill), Анализы (FlaskConical), История (Calendar), Профиль (User) — using Lucide React icons. Active tab highlighted with --tg-theme-button-color. Each tab uses NavLink from react-router-dom for active state. Flex layout: justify-around.
  Must NOT do: Do NOT use emoji for icons — always Lucide React. Do NOT include insurance or FLG tabs (accessible from Profile). Do NOT use fixed positioning without safe-area padding.
  Parallelization: Wave 4 | Blocked by: 2.6 | Blocks: 4.2 | Can parallelize with: 4.3
  References: patterns/mini-app-template/README.md:66-80 (BottomNav pattern with Outlet), frontend/bottom-nav.js:1-75 (current 5-tab nav — Записи/Препараты/Анализы/История/Профиль), frontend/css/app.css:70-122 (BottomNav CSS — flex, justify-around, safe-area, active state)
  Acceptance criteria: 5 tabs render with correct Lucide icons. Active tab highlighted. Click navigates via React Router. Safe-area bottom padding applied. Insurance and FLG NOT in nav.
  QA scenarios: Render BottomNav — 5 items visible. Click Профиль → navigate to /profile. Verify active state styling. Evidence: .omo/evidence/task-4.1-project5-react-migration.txt
  Commit: Y | feat(frontend): create BottomNav with 5 tabs (Lucide icons)

- [ ] 4.2. src/app/routes.tsx: Set up React Router with lazy routes
  What to do: Create route configuration with React Router 7: root layout (AppShell + BottomNav + Outlet), lazy-loaded pages. Routes:
    - / → redirect to /records
    - /records → lazy(() => import('@/features/records/components/RecordsPage'))
    - /medications → lazy(...)
    - /analytics → lazy(...)
    - /history → lazy(...)
    - /profile → lazy(...)
    - /profile/insurance → lazy(InsurancePage)
    - /profile/fluorography → lazy(FlgPage)
  Wrap routes in AuthGate. Profile sub-routes use nested <Outlet />.
  Must NOT do: Do NOT eagerly import pages — all must be lazy(). Do NOT put AuthGate inside page components — wrap once at router level.
  Parallelization: Wave 4 | Blocked by: 2.5, 2.6, 3.4, 4.1 | Blocks: 5.1-5.7 | Can parallelize with: —
  References: patterns/mini-app-template/README.md:15 (React Router 7), patterns/mini-app-template/README.md:26 (lazy routes pattern), frontend/app-state.js:1-145 (current navigation — tab IDs, initial tab from hash, lifecycle hooks)
  Acceptance criteria: 8 routes defined (6 top-level + 2 sub-routes). All use lazy loading. AuthGate wraps all routes. Root layout renders AppShell + BottomNav + Outlet.
  QA scenarios: Visit /records → RecordsPage renders. Visit /profile/insurance → InsurancePage renders with Profile layout. Visit /nonexistent → 404. Evidence: .omo/evidence/task-4.2-project5-react-migration.txt
  Commit: Y | feat(frontend): configure React Router with lazy routes + AuthGate

- [ ] 4.3. src/components/PageShell.tsx: Create reusable page shell with state handling
  What to do: Create PageShell component that accepts: title, loading, error, empty (boolean), onRetry (callback). Renders shadcn Skeleton(s) when loading, shadcn Alert (destructive) with retry button on error, custom empty state with icon/title/subtitle, or children when ready. This replaces window.UI.renderLoading/renderError/renderEmpty pattern.
  Must NOT do: Do NOT use one-off loading/error/empty patterns in pages — always use PageShell. Do NOT hardcode Russian text — accept as props.
  Parallelization: Wave 4 | Blocked by: — | Blocks: — | Can parallelize with: 4.1
  References: frontend/ui-helpers.js:1-121 (renderLoading, renderError, renderEmpty patterns), frontend/css/app.css:124-193 (state placeholder CSS — spinner, error, empty, retry button)
  Acceptance criteria: loading=true → Skeleton(s) shown. error=true + errorMessage → Alert with message and retry. empty=true → custom empty state. All false → children rendered.
  QA scenarios: <PageShell loading={true}><div>content</div></PageShell> → skeleton, not children. <PageShell error={true} errorMessage="Test" onRetry={fn}> → alert with retry. Evidence: .omo/evidence/task-4.3-project5-react-migration.txt
  Commit: Y | feat(frontend): create PageShell component with loading/error/empty states

### WAVE 5: Feature Pages (ALL parallel — 7 tasks)

- [ ] 5.1. src/features/records/: Migrate RecordsPage — day-view health journal
  What to do: Create RecordsPage with: date navigator (prev/today/next), budget banner, 4 expandable slots (vitals/symptoms/visits/notes), symptom entries with severity badges (1-10 scale), key metrics footer (sleep, steps, water, pain score), swipe-to-delete symptoms with undo snackbar, BMR calculator form, supplements manager. API: GET /api/profile/symptoms?from_date=X&to_date=X. Store: Zustand slice (selectedDate, slots, symptoms, visits).
  Must NOT do: Do NOT use innerHTML. Do NOT use DOM manipulation — all React state. Do NOT use window.* globals. Do NOT port BMR calculator CSS-only dead code (no JS counterpart). Do NOT create files >250 lines.
  Parallelization: Wave 5 | Blocked by: 2.1, 2.2, 4.2 | Blocks: — | Can parallelize with: 5.2-5.7
  References: frontend/js/records.js:1-554 (FULL module — date helpers, slots, severity, symptoms CRUD, BMR, supplements, snackbar), frontend/api.js:115-169 (getRecords — composes symptoms+visits), frontend/css/app.css:368-1331 (Records CSS — date nav, budget banner, slots, severity bars, snackbar)
  Acceptance criteria: Date navigator changes selected date. Symptoms load and display with severity badges. Vitals/visits/notes slots expand/collapse. BMR calculator computes values. Swipe-to-delete with undo. Day footer shows key metrics.
  QA scenarios: Navigate to /records → loading → symptoms loaded. Change date → data refreshes. Expand vitals slot → content shown. Delete symptom → undo appears. Evidence: .omo/evidence/task-5.1-project5-react-migration.png (screenshot)
  Commit: Y | feat(frontend): migrate RecordsPage — day-view health journal

- [ ] 5.2. src/features/medications/: Migrate MedicationsPage — drug tracker with CRUD
  What to do: Create MedicationsPage with: medications list with stock progress bars (green >14d, yellow 7-14d, red <7d), prescription expiry badges, supplements section, inline add-medication form (name, dose, stock days, frequency), stock alerts. API: GET /api/pharmacy/, POST /api/pharmacy/. Store: Zustand slice (medications, supplements, formOpen).
  Must NOT do: Do NOT use window.toggleAddForm() / window.addMedication() globals. Do NOT use inline HTML string building. Do NOT use var — const/let only.
  Parallelization: Wave 5 | Blocked by: 2.1, 2.2, 4.2 | Blocks: — | Can parallelize with: 5.1, 5.3-5.7
  References: frontend/js/medications.js:1-249 (FULL module — load, render, stock helpers, add form), frontend/api.js:170-190 (getMedications), app/routes/pharmacy.py:1-255 (CRUD endpoints), frontend/css/app.css:1333-1497 (Medications CSS — .med-card, .stock-track, .rx-badge)
  Acceptance criteria: Medications list renders with stock bars. Green bar: >14 days. Red bar: <7 days. Add form opens inline, submits to API. Prescription badges shown. Supplements section below medications.
  QA scenarios: Navigate to /medications → loading → medications loaded. Click "+ Добавить лекарство" → form appears. Fill form, submit → new medication in list. Evidence: .omo/evidence/task-5.2-project5-react-migration.png
  Commit: Y | feat(frontend): migrate MedicationsPage — drug tracker with CRUD

- [ ] 5.3. src/features/analytics/: Migrate AnalyticsPage — lab test archive with drill-down
  What to do: Create AnalyticsPage with: category accordion cards (from /api/history/categories), year filter pills, expandable record cards with parameter tables (name, value, unit, ref_range, flag with colored dots). 3-level drill-down: category → year → record. API: GET /api/history/categories, GET /api/history/analytics?category=X. Store: Zustand slice (categories, selectedCategory, selectedYear, analyticsItems grouped by test_name+date).
  Must NOT do: Do NOT use string concatenation for tables — use proper JSX table/map. Do NOT hardcode category names — read from API.
  Parallelization: Wave 5 | Blocked by: 2.1, 2.2, 4.2 | Blocks: — | Can parallelize with: 5.1-5.2, 5.4-5.7
  References: frontend/js/analytics.js:1-257 (FULL module — load categories, load analytics, groupFlatItems, render accordion + year pills + records + parameters), frontend/api.js:192-227 (getAnalytics — categories + flat items → grouped), frontend/css/app.css:1499-1787 (Analytics CSS — accordion cards, year pills, record cards, param table)
  Acceptance criteria: Category accordions load from API. Click category → analytics items load. Year pills filter items. Record cards expand with parameter tables. Flag dots colored (green/yellow/red).
  QA scenarios: Navigate to /analytics → loading → categories loaded. Click "Анализы" → parameters shown. Click year pill → filtered. Click record → expands with parameter table. Evidence: .omo/evidence/task-5.3-project5-react-migration.png
  Commit: Y | feat(frontend): migrate AnalyticsPage — lab test archive with drill-down

- [ ] 5.4. src/features/history/: Migrate HistoryPage — visit history by year
  What to do: Create HistoryPage with: year-grouped visit cards (doctor, specialty, date, time, institution, purpose, status badge, recommendations). Sorted by date descending. API: GET /api/history/visits. Store: Zustand slice (visits, groupedByYear).
  Must NOT do: Do NOT use MutationObserver to detect tab activation — React Router handles this. Do NOT use inline styles — all Tailwind.
  Parallelization: Wave 5 | Blocked by: 2.1, 2.2, 4.2 | Blocks: — | Can parallelize with: 5.1-5.3, 5.5-5.7
  References: frontend/js/history.js:1-127 (FULL module — load, groupByYear, render visit cards), frontend/api.js:228-235 (getHistory), app/schemas/visit.py:1-62 (VisitSchema, DiagnosticFinding)
  Acceptance criteria: Visits load and group by year. Each visit card shows: doctor, specialty, date, reason. Status badge shown (planned/pending/completed/cancelled). Recommendations collapsible.
  QA scenarios: Navigate to /history → loading → visits grouped by year. Verify visit card fields. Evidence: .omo/evidence/task-5.4-project5-react-migration.png
  Commit: Y | feat(frontend): migrate HistoryPage — visit history by year

- [ ] 5.5. src/features/profile/: Migrate ProfilePage — patient card + sub-routes
  What to do: Create ProfilePage with: personal info (full name, birth date), diagnoses list with status badges (🔴/🟡/✅ → colored badges), allergies list, treatment strategy steps (grouped by section with priority order), document links section (Insurance → /profile/insurance, Fluorography → /profile/fluorography), app version footer. Sub-routes render InsurancePage and FluorographyPage inline. API: GET /api/profile/, GET /api/profile/strategy. Store: Zustand slice (profile, strategy).
  Must NOT do: Do NOT create separate top-level routes for insurance/FLG — must be sub-routes. Do NOT use emoji for status — use shadcn Badge variants.
  Parallelization: Wave 5 | Blocked by: 2.1, 2.2, 4.2 | Blocks: — | Can parallelize with: 5.1-5.4, 5.6-5.7
  References: frontend/js/profile.js:1-157 (FULL module — load profile+strategy, render personal info, diagnoses, strategy steps, document links), frontend/api.js:240-260 (getProfile — maps full_name→fullName, birth_date→birthDate, source→since), app/schemas/profile.py:1-42 (ProfileSchema, DiagnosisItem), app/schemas/strategy.py:1-53 (StrategySchema, StrategyStep), frontend/css/app.css:1789-1803 (Profile CSS — .diagnosis-badge)
  Acceptance criteria: Profile info renders (full name, birth date). Diagnoses with status badges. Allergies list. Strategy steps grouped by section. Document links navigate to sub-routes (/profile/insurance, /profile/fluorography). Version footer shown.
  QA scenarios: Navigate to /profile → loading → profile data rendered. Click "Страховка" link → /profile/insurance renders InsurancePage. Click "Флюорография" → /profile/fluorography renders FlgPage. Evidence: .omo/evidence/task-5.5-project5-react-migration.png
  Commit: Y | feat(frontend): migrate ProfilePage — patient card with sub-routes

- [ ] 5.6. src/features/insurance/: Migrate InsurancePage — insurance policy tracker
  What to do: Create InsurancePage (rendered as sub-route of Profile or standalone). Shows: policy cards with progress bars (spent / sum_insured), color-coded (green <50%, yellow 50-90%, red >90%), total remaining balance row, back button to Profile. API: GET /api/insurance/. Store: Zustand slice (policies).
  Must NOT do: Do NOT add InsurancePage to BottomNav — only accessible via Profile.
  Parallelization: Wave 5 | Blocked by: 2.1, 2.2, 4.2 | Blocks: — | Can parallelize with: 5.1-5.5, 5.7
  References: frontend/js/insurance.js:1-134 (FULL module — load, render policy cards with progress bars), app/schemas/insurance.py:1-44 (InsuranceSchema, InsurancePolicy — sum_insured, spent, remaining, expiry), frontend/css/app.css:1805-1915 (Insurance CSS — .supp-progress-card/track/fill)
  Acceptance criteria: Policy cards render with progress bars. Spent/sum_insured ratio shown. Color coding: green <50%, yellow 50-90%, red >90%. Total row shown. Back button navigates to /profile.
  QA scenarios: Navigate to /profile/insurance → loading → policies loaded. Verify progress bar colors. Click back → returns to /profile. Evidence: .omo/evidence/task-5.6-project5-react-migration.png
  Commit: Y | feat(frontend): migrate InsurancePage — policy tracker with progress bars

- [ ] 5.7. src/features/fluorography/: Migrate FluorographyPage — FLG exam tracker
  What to do: Create FluorographyPage (rendered as sub-route of Profile or standalone). Shows: next due date with highlight (overdue = red, upcoming = yellow, ok = green), history list of past exams (date, reference number, result, institution), back button to Profile. API: GET /api/fluorography/. Store: Zustand slice (nextDue, history).
  Must NOT do: Do NOT add FluorographyPage to BottomNav — only accessible via Profile.
  Parallelization: Wave 5 | Blocked by: 2.1, 2.2, 4.2 | Blocks: — | Can parallelize with: 5.1-5.6
  References: frontend/js/flg.js:1-101 (FULL module — load, render next due + history list), app/schemas/fluorography.py:1-32 (FluorographySchema — next_due, history[]), frontend/css/app.css:1917-1919 (FLG CSS — minimal, uses settings patterns)
  Acceptance criteria: Next due date shown with color coding. History list with date, number, result, institution. Back button navigates to /profile.
  QA scenarios: Navigate to /profile/fluorography → loading → FLG data loaded. Verify next_due color (red if past, yellow if <30d, green otherwise). History cards shown. Evidence: .omo/evidence/task-5.7-project5-react-migration.png
  Commit: Y | feat(frontend): migrate FluorographyPage — FLG exam tracker

### WAVE 6: Polish + Deploy

- [ ] 6.1. src/app/: Add framer-motion page transitions
  What to do: Add AnimatePresence wrapper around <Outlet /> in AppShell. Each page component wraps content in motion.div with fade+slide animation (opacity: 0→1, x: 20→0). Duration: 200ms. Use layoutId for shared element transitions between profile sub-routes.
  Must NOT do: Do NOT animate BottomNav — keep it static. Do NOT use spring animations — use tween for consistency. Do NOT exceed 250ms transitions.
  Parallelization: Wave 6 | Blocked by: — | Blocks: — | Can parallelize with: 6.2-6.5
  References: patterns/mini-app-template/README.md (no specific animation pattern — use framer-motion best practices)
  Acceptance criteria: Page transitions have fade+slide animation (200ms). Back navigation animates in reverse. Profile → Insurance transition animates smoothly.
  QA scenarios: Navigate between pages — verify smooth 200ms transitions. Use browser back button — reverse animation. Evidence: .omo/evidence/task-6.1-project5-react-migration.mp4 (screen recording)
  Commit: Y | feat(frontend): add framer-motion page transitions (fade+slide, 200ms)

- [ ] 6.2. src/hooks/useTelegramTheme.ts: Add dark/light theme toggle + persistence
  What to do: Extend useTelegramTheme hook to: detect Telegram colorScheme (light/dark), apply Tailwind dark class, persist preference in localStorage (overrides Telegram default), expose toggleTheme() function. Update globals.css with dark mode CSS variables (--tg-theme-* dark variants).
  Must NOT do: Do NOT flash wrong theme on load — read localStorage before first render. Do NOT hardcode dark colors — use Telegram theme params.
  Parallelization: Wave 6 | Blocked by: — | Blocks: — | Can parallelize with: 6.1, 6.3-6.5
  References: patterns/mini-app-template/README.md:99-105 (Telegram CSS variables — light and dark mode), frontend/app-shell.js:1-185 (theme application — tg.themeParams, colorScheme), frontend/css/app.css:1921-2062 (dark theme @media overrides)
  Acceptance criteria: Theme switches between light/dark. Persisted to localStorage. Tailwind dark class applied correctly. All shadcn/ui components respect theme.
  QA scenarios: Set dark mode → page renders with dark colors. Reload → dark mode persists. Clear localStorage → resets to Telegram default. Evidence: .omo/evidence/task-6.2-project5-react-migration.png (dark) + .omo/evidence/task-6.2b-project5-react-migration.png (light)
  Commit: Y | feat(frontend): add dark/light theme toggle with persistence

- [ ] 6.3. public/version.json + src/lib/version.ts: Implement cache busting with version.json
  What to do: Create version.json in public/ with {"version": "<timestamp>"} updated on each build (via Vite plugin or build script). Create useVersionCheck hook that: fetches version.json on mount, compares with sessionStorage, forces reload on mismatch. This replaces the inline script in current index.html.
  Must NOT do: Do NOT use blocking XHR (sync) — use async fetch. Do NOT delete version.json during build.
  Parallelization: Wave 6 | Blocked by: — | Blocks: — | Can parallelize with: 6.1-6.2, 6.4-6.5
  References: frontend/index.html:14-34 (current cache-busting — XHR version.json, sessionStorage compare, window.location.reload), frontend/main.py:44 (server deployment: scp + version.json creation)
  Acceptance criteria: version.json fetched on mount. Version mismatch triggers reload. Same version — no reload. version.json updated during build (timestamp or git hash).
  QA scenarios: Build, deploy, load app → version stored. Rebuild with new version, reload → app reloads once. Evidence: .omo/evidence/task-6.3-project5-react-migration.txt (console logs showing version check)
  Commit: Y | feat(frontend): implement version.json cache busting

- [ ] 6.4. vite.config.ts: Finalize Vite build config for production
  What to do: Configure: base: '/sh/', build.outDir: 'dist', build.assetsDir: 'assets', server.port: 5173, server.proxy: { '/api': 'http://localhost:8000' } for dev. Add build.rollupOptions.output.manualChunks for vendor splitting (react, react-dom, shadcn, telegram-ui, framer-motion as separate chunks). Add build.target: 'es2020' for broad mobile support.
  Must NOT do: Do NOT change base from /sh/. Do NOT remove proxy config (needed for Telegram Mini App testing).
  Parallelization: Wave 6 | Blocked by: — | Blocks: 6.5 | Can parallelize with: 6.1-6.3
  References: frontend/vite.config.js:1-14 (current config — base /sh/, outDir dist, port 5173), patterns/mini-app-template/README.md:11 (Vite 6), frontend/main.py:46 (deploy: scp -r frontend/dist/* to VPS)
  Acceptance criteria: `npm run build` succeeds. dist/ contains index.html, assets/, sw.js, manifest.webmanifest, version.json. base='/sh/' applied to all asset paths. Dev server proxies /api to backend.
  QA scenarios: `npm run build` → exit 0. Inspect dist/index.html → script/link paths start with /sh/. `npm run dev` → /api/health proxied to :8000. Evidence: .omo/evidence/task-6.4-project5-react-migration.txt
  Commit: Y | chore(frontend): finalize Vite production build config

- [ ] 6.5. frontend/: Deployment verification + old code cleanup
  What to do: Run `npm run build`. Verify dist/ contains all expected files. Run backend with `uvicorn app.main:app` and serve dist/ via FastAPI static mount. Smoke-test ALL 11 API endpoints: curl /api/profile/, /api/pharmacy/, /api/history/visits, /api/history/analytics, /api/history/categories, /api/insurance/, /api/fluorography/, /api/profile/strategy, /api/profile/symptoms, /api/me, /health. Only AFTER all endpoints verified → delete old frontend files: js/*.js, api.js, app-state.js, ui-helpers.js, app-shell.js, bottom-nav.js, css/app.css, old index.html (keep as .bak). Update main.js to import React app.
  Must NOT do: Do NOT delete old files before build+verification passes. Do NOT touch backend files. Do NOT commit deleted files without verification.
  Parallelization: Wave 6 | Blocked by: 6.4 | Blocks: — | Can parallelize with: 6.1-6.3
  References: frontend/main.py:1-113 (FastAPI static mount), frontend/main.py:36-48 (deploy commands), ALL frontend/ files to clean up
  Acceptance criteria: `npm run build` succeeds. All 11 API endpoints return 200 from served app. Old vanilla JS files deleted. React app serves from root.
  QA scenarios: Start backend + serve dist → open browser → React app loads. Navigate all 7 pages → data loads from API. curl all endpoints → 200. Evidence: .omo/evidence/task-6.5-project5-react-migration.txt (smoke test results)
  Commit: Y | chore(frontend): deploy React build + cleanup old vanilla JS files

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.

- [ ] F1. Plan compliance audit: Did all 30 tasks complete? Did any task deviate from plan? Are all acceptance criteria met?
- [ ] F2. Code quality review: tsc --noEmit strict mode (0 errors), no `any` types, no `@ts-ignore`, no files >250 LOC, all imports use path aliases (@/), no residual window.* globals
- [ ] F3. End-to-end QA: Serve app, navigate all 7 pages, verify ALL 11 API endpoints return data, test auth flow (401→401, 403→pending screen, 200→app), test PWA install on mobile, test theme toggle light/dark, test navigation all tabs + sub-routes
- [ ] F4. Scope fidelity: Nothing added beyond plan scope. Nothing missing from Must have list. All Must NOT have rules respected.

## Commit strategy
- Each todo = one atomic commit with format: `<type>(frontend|backend): <description>`
- Wave 1-4 commits are sequential (dependencies)
- Wave 5 commits can be parallel (feature pages are independent) — use feature branches + merge
- Wave 6 commits are sequential (final polish)
- Final commit after F1-F4 verification: `chore: complete React migration — cleanup old frontend`

## Success criteria
1. React app builds with `npm run build` (0 errors, 0 warnings)
2. TypeScript strict mode: `tsc --noEmit` passes
3. All 11 API endpoints return data when called from React app
4. All 7 pages render with correct data (matching vanilla JS behavior)
5. BottomNav has exactly 5 tabs (insurance + FLG in Profile sub-routes)
6. Auth: Telegram initData flow works, 403 pending_approval shows pending screen
7. PWA: Service Worker registered, app installable on Android/iOS, stored token auth works
8. Theme: dark/light toggle works, Telegram theme colors applied
9. Cache busting: version.json triggers reload on deploy
10. Old vanilla JS files removed, only React frontend remains
11. Backend unchanged except 1 new route (POST /api/auth/pwa)
12. Zero `any` types, zero `@ts-ignore`, zero files >250 LOC
