# Project5 Refactoring Plan — Sasha Health Mini App → Reference Architecture

**Goal**: Refactor P5 vanilla JS Mini App to match the architectural quality of P1/P3 React Mini Apps — AppShell, BottomNav, centralized state, loading/error/empty states, Safe-area, Telegram theme.

**Scope**: Frontend only. Backend untouched. No React, no jQuery. Vanilla JS + Vite.

**Created**: 2026-07-03 | **Status**: DRAFT

---

## 1. Current State Audit

### 1.1 Architecture Gaps

| What | P5 (Current) | P1/P3 (Reference) |
|------|-------------|-------------------|
| Shell | `body { max-width: 480px }` in CSS — no structural wrapper | AppShell div → flex column → content + BottomNav |
| Routing | `window.switchTab('records')` — global function | Router (React Router / HashRouter) |
| State | Per-module `var state = {...}` — isolated, no cross-tab awareness | Centralized store (Zustand / prop drilling) |
| Nav | 7 tabs in `.tab-bar` | BottomNav component, 3-4 tabs |
| Loading | Inconsistent — some show `innerHTML`, some don't | Standardized loading spinner/placeholder |
| Error | Inconsistent — some catch blocks, some none | ErrorBoundary + per-page error states |
| Empty | Mixed — some tabs show "нет данных", others silently blank | Consistent empty state UI |
| Theme | Mix of `prefers-color-scheme` + `var(--tg-theme-*)` | Predominantly `var(--tg-theme-*)` |
| Safe-area | Partial — tab-bar only | AppShell handles inset-top/bottom universally |
| Duplication | `escapeHtml` in 4 files, `formatDate` in 3 files | Shared utilities |

### 1.2 Problematic Patterns

1. **Eager loading**: `loadMedications()`, `loadHistory()`, `loadProfile()` fire on script init even when tab is not active. Records tab is the exception (lazy via `switchTab` hook).
2. **Inline HTML construction**: All modules build HTML via string concatenation — error-prone, no escaping by default.
3. **No tab lifecycle**: No `onTabEnter` / `onTabLeave` hooks. Each module monkey-patches `switchTab` or uses MutationObserver.
4. **CSS sprawl**: 950 lines across 2 files, overlapping concerns, duplicate dark-mode blocks.
5. **Magic numbers**: `max-width: 480px` in settings.css body, `max-width: 480px` in records.css tab-bar — inconsistent.
6. **`tg.ready()` and `tg.expand()` called in multiple modules** — should be once in AppShell.

---

## 2. Target Architecture

### 2.1 Structural Diagram

```
index.html
  └── #app (root mount point)
       └── app-shell.js → creates:
            ├── .app-shell__container (max-width 500px, centered, flex column)
            │    ├── .app-shell__header (sticky, optional — currently not present)
            │    └── .app-shell__content (flex: 1, overflow-y: auto)
            │         ├── [tab panels with class .tab-panel — lazy rendered]
            │         └── .state-placeholder (loading / error / empty components)
            └── bottom-nav.js → creates:
                 └── .bottom-nav (fixed bottom, 5 tabs)
```

### 2.2 Module Map

```
frontend/
├── index.html          ← simplified: only #app mount + Telegram SDK
├── main.js             ← imports shell + nav, initializes App
├── app-shell.js        ← AppShell container, safe-area, theme init
├── bottom-nav.js       ← BottomNav component (5 tabs)
├── app-state.js        ← Centralized App.state (shared across modules)
├── ui-helpers.js       ← escapeHtml, formatDate, renderState (loading/error/empty)
├── api.js              ← unchanged (already well-structured)
├── js/
│   ├── records.js      ← refactored: uses App.state.tabs.records, lazy load
│   ├── medications.js  ← refactored: uses App.state.tabs.medications, lazy load
│   ├── analytics.js    ← refactored: uses App.state.tabs.analytics, lazy load
│   ├── history.js      ← refactored: uses App.state.tabs.history, lazy load
│   ├── profile.js      ← refactored: uses App.state.tabs.profile, lazy load
│   ├── insurance.js    ← moved: accessible from Profile tab, not in BottomNav
│   └── flg.js          ← moved: accessible from Profile tab, not in BottomNav
└── css/
    └── app.css         ← unified stylesheet: shell + nav + tabs + theme + safe-area
                         (merged records.css + settings.css, deduplicated, reorganized)
```

### 2.3 BottomNav Tab Reduction (7 → 5)

| # | Old Tab | New Tab | Icon | Action |
|---|---------|---------|------|--------|
| 1 | 📋 Записи | 📋 Записи | 📋 | `App.navigate('records')` |
| 2 | 💊 Препараты | 💊 Препараты | 💊 | `App.navigate('medications')` |
| 3 | 🔬 Анализы | 🔬 Анализы | 🔬 | `App.navigate('analytics')` |
| 4 | 🛡 Страховка | **REMOVED** | — | Accessible via Profile tab as sub-section |
| 5 | 📅 История | 📅 История | 📅 | `App.navigate('history')` |
| 6 | 🩻 ФЛГ | **REMOVED** | — | Accessible via Profile tab as sub-section |
| 7 | 👤 Профиль | 👤 Профиль | 👤 | `App.navigate('profile')` |

Profile tab gains two sub-sections: "Страховка" (insurance) and "Флюорография" (FLG) — rendered inline using existing modules.

---

## 3. Component Specifications

### 3.1 AppShell (`app-shell.js`)

**Purpose**: Root container. Initializes Telegram, sets theme CSS variables, manages safe-area.

```js
// Pattern from P3 AppShell:
// - display: flex; flex-direction: column; height: 100vh; max-width: 500px; margin: 0 auto
// - overflow: hidden
// - Content area: flex: 1; overflow-y: auto
// - BottomNav: flex-shrink: 0
```

**Responsibilities**:
- Call `tg.ready()` and `tg.expand()` **once**
- Set `--tg-safe-area-inset-top` and `--tg-safe-area-inset-bottom` CSS variables
- Apply Telegram theme colors as CSS variables (from `tg.themeParams`)
- Mount BottomNav component
- Create content area for tab panels

**API**:
```js
window.App = {
  state: { currentTab: 'records', ...tabStates },
  navigate(tabName),
  onTabEnter(tabName, callback),
  onTabLeave(tabName, callback),
}
```

### 3.2 BottomNav (`bottom-nav.js`)

**Purpose**: Fixed bottom navigation bar with 5 tabs. Pattern from P3 `BottomNav`:

```js
// P3 pattern:
// nav { display: flex; justify-content: space-around; padding: 8px 0; pb: calc(8px + env(safe-area-inset-bottom)) }
// button { flex-direction: column; align-items: center; gap: 3px; }
// active state: color = var(--tg-theme-button-color)
```

**Features**:
- 5 tab buttons: Записи, Препараты, Анализы, История, Профиль
- Active tab highlight (accent color + bold label)
- Click → `App.navigate(tabName)`
- Safe-area bottom padding
- No horizontal scroll (unlike current 7-tab overflow)

### 3.3 Centralized State (`app-state.js`)

```js
window.App.state = {
  currentTab: 'records',

  tabs: {
    records:    { status: 'idle', data: null, error: null },
    medications:{ status: 'idle', data: null, error: null },
    analytics:  { status: 'idle', data: null, error: null },
    history:    { status: 'idle', data: null, error: null },
    profile:    { status: 'idle', data: null, error: null },
    insurance:  { status: 'idle', data: null, error: null },
    flg:        { status: 'idle', data: null, error: null },
  },

  // Design tokens
  theme: {
    bgColor: '',
    textColor: '',
    hintColor: '',
    buttonColor: '',
    secondaryBgColor: '',
  }
};
```

**Status lifecycle**: `idle → loading → (success | error)`. On success, `data` populated. On error, `error` populated. On `navigate` back to idle tab, re-trigger load.

### 3.4 UI Helpers (`ui-helpers.js`)

Standardized rendering functions used by ALL tab modules:

```js
window.UI = {
  escapeHtml(str),                    // shared XSS prevention
  formatDate(iso, format),            // shared date formatting
  renderLoading(containerId),         // standardized spinner
  renderError(containerId, message),   // standardized error with retry
  renderEmpty(containerId, icon, title, subtitle),  // standardized empty state
}
```

**Loading state** (pattern from P3):
```html
<div class="state-placeholder">
  <div class="spinner"></div>
  <p>Загрузка...</p>
</div>
```

**Error state** (pattern from P1 ErrorBoundary + P3):
```html
<div class="state-placeholder state-error">
  <div class="state-icon">⚠️</div>
  <p class="state-title">Ошибка загрузки</p>
  <p class="state-message">[error details]</p>
  <button class="state-retry" onclick="...">Попробовать снова</button>
</div>
```

**Empty state** (pattern from existing P5 history empty):
```html
<div class="state-placeholder state-empty">
  <div class="state-icon">[icon]</div>
  <p class="state-title">[title]</p>
  <p class="state-subtitle">[subtitle]</p>
</div>
```

### 3.5 Tab Lifecycle

```js
// AppShell manages tab lifecycle
App.navigate = function(tabName) {
  // 1. Hide current tab panel
  // 2. Show target tab panel (create if not exists)
  // 3. If first visit → trigger lazy load
  // 4. Update BottomNav active state
  // 5. Update App.state.currentTab
};

App.onTabEnter = function(tabName, callback) {
  // Register callback for when tab becomes visible
};

// Each tab module:
App.onTabEnter('medications', function() {
  if (App.state.tabs.medications.status === 'idle') {
    loadMedications();
  }
});
```

### 3.6 Tab Module Refactoring (each module)

Every module must follow this contract:

```js
// js/[module].js
(function() {
  'use strict';

  // 1. Get container reference
  var container = document.getElementById('[module]-section');

  // 2. Register lazy-load hook
  App.onTabEnter('[module]', function() {
    if (App.state.tabs.[module].status === 'idle') {
      load();
    }
  });

  // 3. Load function
  async function load() {
    App.state.tabs.[module].status = 'loading';
    UI.renderLoading('[module]-container');

    try {
      var data = await API.get[Module]();
      if (!data || isEmpty(data)) {
        App.state.tabs.[module].status = 'empty';
        UI.renderEmpty('[module]-container', 'icon', 'title', 'subtitle');
      } else {
        App.state.tabs.[module].status = 'success';
        App.state.tabs.[module].data = data;
        render(data);
      }
    } catch (e) {
      App.state.tabs.[module].status = 'error';
      App.state.tabs.[module].error = e.message;
      UI.renderError('[module]-container', e.message);
    }
  }

  // 4. Render function (module-specific)
  function render(data) { ... }

  // 5. Remove eager init
  // NO: load[Module](); at bottom of file
})();
```

### 3.7 Profile Tab — Sub-sections

Profile tab gains two additional sections beyond current data:

```html
<!-- After "Стратегия лечения" group -->
<div class="group-title">Документы</div>
<div class="settings-group">
  <div class="settings-row clickable" onclick="App.navigate('insurance')">
    <div class="row-label">🛡 Страховка</div>
    <div class="row-chevron">›</div>
  </div>
  <div class="settings-row clickable" onclick="App.navigate('flg')">
    <div class="row-label">🩻 Флюорография</div>
    <div class="row-chevron">›</div>
  </div>
</div>
```

Insurance and FLG render inline within their own hidden tab panels (not in BottomNav). Navigating to them shows a back button to return to profile.

---

## 4. CSS Restructuring Plan

### 4.1 Merge Strategy

Combine `records.css` + `settings.css` → `app.css` in logical sections:

```css
/* === 1. RESET & BASE ======================================== */
/* Box-sizing, body defaults, font */

/* === 2. CSS CUSTOM PROPERTIES (Theme) ======================= */
/* :root { --tg-* fallbacks, --medical-* colors, --app-* tokens } */

/* === 3. APP SHELL =========================================== */
/* .app-shell, .app-shell__container, .app-shell__content */

/* === 4. BOTTOM NAV ========================================== */
/* .bottom-nav, .bottom-nav__item, active states, safe-area */

/* === 5. STATE PLACEHOLDERS ================================== */
/* .state-placeholder, .spinner, .state-error, .state-empty */

/* === 6. TAB PANELS (shared) ================================= */
/* .tab-panel, .section, padding, scroll */

/* === 7. SETTINGS LIST (shared) ============================== */
/* .settings-group, .settings-row, .group-title, .row-label, etc. */

/* === 8. RECORDS (records tab specific) ====================== */
/* .slot, .budget-banner, .day-footer, .bar-*, .snackbar */

/* === 9. MEDICATIONS (medications tab specific) ============== */
/* .med-card, .stock-*, .rx-badge, .add-med-form */

/* === 10. ANALYTICS (analytics tab specific) ================= */
/* .analytics-*, .record-*, .param-*, .year-pill */

/* === 11. PROFILE (profile tab specific) ===================== */
/* .diagnosis-badge, .profile-header */

/* === 12. INSURANCE (insurance tab specific) ================= */
/* .supp-progress-* */

/* === 13. FLG (flg tab specific) ============================== */
/* (minimal — uses settings-list patterns) */

/* === 14. RESPONSIVE ========================================= */
/* @media (max-width: 375px) adjustments */

/* === 15. DARK THEME OVERRIDES =============================== */
/* @media (prefers-color-scheme: dark) fallbacks */
```

### 4.2 Deduplication Targets

1. **Dark theme blocks**: 12+ duplicate `@media (prefers-color-scheme: dark)` blocks → consolidate to sections 14-15
2. **Responsive blocks**: 2 duplicate `@media (max-width: 375px)` → single section
3. **Card border styles**: `.card-ok/.card-warn/.card-danger` duplicated similarly → shared
4. **Body rules**: 2 competing `body {}` blocks → single in section 1

### 4.3 Telegram Theme Variables (MANDATORY)

Replace ALL hardcoded colors with `var(--tg-theme-*)`:

| Old | New |
|-----|-----|
| `#fff` (bg) | `var(--tg-theme-bg-color, #fff)` |
| `#222` (text) | `var(--tg-theme-text-color, #222)` |
| `#8e8e93` (hint) | `var(--tg-theme-hint-color, #8e8e93)` |
| `#2a7ae2` (accent) | `var(--tg-theme-button-color, #2a7ae2)` |
| `#f2f2f7` / `#e5e5ea` (secondary) | `var(--tg-theme-secondary-bg-color, #f2f2f7)` |
| `#1c1c1e` (dark bg) | `var(--tg-theme-bg-color, #1c1c1e)` |

Hardcoded warm-stone tab bar colors (`#e8e3dc`, `#9a9187`, etc.) → use Telegram theme variables instead.

---

## 5. Implementation Sequence (13 steps)

### Phase 1: Foundation (no visual change)

**Step 1**: Create `frontend/css/app.css` — merged, organized, Telegram-themed, deduplicated. All `var(--tg-theme-*)` with fallbacks. Safe-area universal. (Keep old CSS files in place during transition.)

**Step 2**: Create `frontend/ui-helpers.js` — `escapeHtml`, `formatDate`, `renderLoading`, `renderError`, `renderEmpty`.

**Step 3**: Create `frontend/app-state.js` — `window.App` namespace with `state`, `navigate()`, `onTabEnter()`/`onTabLeave()` lifecycle.

### Phase 2: Shell

**Step 4**: Create `frontend/app-shell.js` — Mount `#app`, create container + content area, init Telegram (once), apply theme vars, wire safe-area.

**Step 5**: Create `frontend/bottom-nav.js` — 5-tab BottomNav, active tracking, `App.navigate()` integration.

**Step 6**: Rewrite `frontend/index.html` — minimal: `#app` mount, Telegram SDK, `<link>` to new `app.css`, `<script type="module" src="/main.js">`.

**Step 7**: Update `frontend/main.js` — import `app-shell.js`, `app-state.js`, `bottom-nav.js`, `ui-helpers.js`, `api.js`, then all tab modules.

### Phase 3: Tab Modules (one at a time, parallelizable)

**Step 8**: Refactor `js/profile.js` — adopt lifecycle contract. Add insurance + FLG sub-links.

**Step 9**: Refactor `js/medications.js` — adopt lifecycle contract. Remove inline CSS `<style>` injection → move to `app.css`.

**Step 10**: Refactor `js/analytics.js` — adopt lifecycle contract.

**Step 11**: Refactor `js/history.js` — adopt lifecycle contract. Remove MutationObserver hack.

**Step 12**: Refactor `js/records.js` — adopt lifecycle contract.

**Step 13**: Update `js/insurance.js` and `js/flg.js` — adopt lifecycle contract (triggered from Profile sub-links, not auto-init).

### Phase 4: Cleanup

**Step 14**: Delete old CSS files (`records.css`, `settings.css`).

**Step 15**: Remove dead code: old `switchTab` global, old `window.__records`, duplicate `escapeHtml` definitions.

**Step 16**: Verify all 7 endpoints still work end-to-end.

---

## 6. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| CSS merge breaks visual layout | Keep old CSS until new CSS verified. Switch atomically in index.html. |
| `tg.*` calls missing after refactor | All `tg.ready()`/`tg.expand()` consolidated in `app-shell.js` |
| Tab modules assume `document.ready` state | All modules use `App.onTabEnter` which fires after DOM exists |
| `window.API` not available when modules load | ES module import order in `main.js` guarantees `api.js` runs first |
| Regression on non-refactored tabs | Each tab refactored independently — can test one at a time |

---

## 7. Verification Checklist

- [x] AppShell renders centered container (max-width 500px)
- [x] BottomNav shows exactly 5 tabs, active state works
- [x] Tab switching: each tab loads data on first visit, caches data on return
- [x] Loading spinner shows on first visit to each tab
- [x] Error state shows with retry button when API fails
- [x] Empty state shows when API returns no data
- [x] Profile tab includes insurance + FLG sub-links
- [x] Insurance/FLG render with back button to profile
- [x] Telegram theme colors apply correctly in both light and dark modes
- [x] Safe-area padding works on notched devices (iPhone X+)
- [x] All 7 API endpoints still functional: `/api/pharmacy/`, `/api/history/categories`, `/api/history/analytics`, `/api/history/visits`, `/api/profile/`, `/api/insurance/`, `/api/fluorography/`
- [x] `escapeHtml` used consistently across all modules
- [x] No `escapeHtml` duplication across files
- [x] No hardcoded colors without `var(--tg-theme-*)` fallback
- [x] Old CSS files removed
- [x] No eager loading (modules don't fetch on script init)
- [x] Vite build succeeds: `npm run build`
