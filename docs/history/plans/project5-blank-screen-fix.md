# project5-blank-screen-fix — Work Plan

## TL;DR (For humans)

**Что сломалось:** После React-миграции Mini App показывает пустой экран в Телеграме. JS-файл не загружается — сервер отдаёт HTML вместо JavaScript.

**Почему:** Vite собирает с `base: /sh/`, генерируя `<script src="/sh/assets/index-*.js">`. FastAPI монтирует статику на корень `/`, поэтому запрос `/sh/assets/index-*.js` ищет файл `frontend/dist/sh/assets/index-*.js` (не существует). SPA-fallback (`html=True`) отдаёт `index.html` вместо JS → браузер парсит HTML как JavaScript → SyntaxError → blank screen.

**План:** 1 правка в `main.py` — сменить mount с `/` на `/sh`. Плюс чистка мусора (мёртвый CSS, старые vanilla JS файлы, дубликат vite.config.js). 5 минут.

**Что НЕ делает:**
- НЕ трогает бэкенд-логику (auth, storage, API routes)
- НЕ меняет фронтенд-код
- НЕ добавляет новые фичи

**Effort:** XS (1 критическая правка + чистка)
**Risk:** Minimal — одна строка

---

## Scope

### Must have
- [ ] `app/main.py`: mount static at `/sh` instead of `/` (FIX ROOT CAUSE)
- [ ] Verify build succeeds (`npm run build`)
- [ ] Check `lsp_diagnostics` clean on changed files

### Should have
- [ ] Delete `frontend/css/app.css` — 2156 lines dead vanilla JS CSS
- [ ] Delete `frontend/vite.config.js` — dead code (Vite uses `.ts`)
- [ ] Clean up old vanilla JS files: `main.js`, `app-shell.js`, `bottom-nav.js`, `api.js`, `app-state.js`, `ui-helpers.js`, `js/*.js`

### Nice to have
- [ ] Add nginx config template to repo (`deploy/nginx.conf`)
- [ ] Create `.env.production` with `VITE_API_BASE=` for clarity

---

## Todo

### Wave 1: Root Cause Fix

- [x] **`app/main.py:115`: Change mount from `/` to `/sh`** — исправить `app.mount("/", ...)` → `app.mount("/sh", ...)` чтобы StaticFiles корректно резолвил `/sh/assets/...` → `frontend/dist/assets/...`. Это единственная критическая правка.
  - *Acceptance*: Локально `curl http://localhost:8000/sh/` отдаёт `index.html` с правильным Content-Type. `curl http://localhost:8000/sh/assets/index-*.js` отдаёт JS (не HTML).
  - *QA*: `lsp_diagnostics app/main.py` clean. `bash` запуск uvicorn и проверка curl.

- [x] **`app/main.py`: Add redirect from `/` to `/sh/`** — чтобы корень не 404.
  - *Acceptance*: `curl -L http://localhost:8000/` → 302 → `/sh/` → 200 index.html
  - *QA*: `lsp_diagnostics` clean. Curl проверка.

### Wave 2: Build Verification

- [x] **Run `npm run build` in `frontend/`** — убедиться что React-сборка проходит без ошибок.
  - *Acceptance*: Exit code 0, `dist/` содержит index.html + assets/.
  - *QA*: `bash` run + check exit code.

- [x] **Verify `dist/index.html` asset paths** — проверить что все ссылки с префиксом `/sh/`.
  - *Acceptance*: Все `<script src="...">` и `<link href="...">` начинаются с `/sh/`.
  - *QA*: `read dist/index.html` и grep на `<script`, `<link`.

### Wave 3: Cleanup Dead Code

- [x] **Delete `frontend/css/app.css`** — 2156 строк мёртвого CSS из vanilla JS эры
- [x] **Delete `frontend/vite.config.js`** — дубликат vite.config.ts
- [x] **Delete old vanilla JS files** — `main.js`, `app-shell.js`, `bottom-nav.js`, `api.js`, `app-state.js`, `ui-helpers.js`, `frontend/js/*.js`
  - *Acceptance*: `npm run build` всё ещё проходит, `lsp_diagnostics` clean.
  - *QA*: `bash npm run build` success.

---

## Root Cause Diagram

```
Browser requests: GET /sh/assets/index-B09nX405.js
         │
         ▼
    [nginx]  (either serves static OR proxies to FastAPI)
         │
         ▼
    [FastAPI:8000]
    app.mount("/", StaticFiles(directory="frontend/dist"))
         │
         ▼
    Looks for: frontend/dist/sh/assets/index-B09nX405.js  ← DOESN'T EXIST
         │
         ▼
    html=True fallback: serves frontend/dist/index.html AS JS  ← WRONG MIME
         │
         ▼
    Browser: SyntaxError (HTML is not valid JavaScript)
         │
         ▼
    BLANK SCREEN
```

**After fix** (`app.mount("/sh", ...)`):
```
GET /sh/assets/index-B09nX405.js
         │
         ▼
    FastAPI strips /sh → looks for assets/index-B09nX405.js
         │
         ▼
    Found: frontend/dist/assets/index-B09nX405.js  ← EXISTS ✓
         │
         ▼
    Serves with correct MIME type (application/javascript)
         │
         ▼
    Browser executes JS → React mounts → APP RENDERS ✓
```
