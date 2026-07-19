# project5-redesign — Work Plan

## TL;DR (For humans)

**What you'll get:** Полный редизайн Sasha Health — тёмная дизайн-система, профиль как главная страница с аватаркой, отдельные страницы диагнозов и аллергий, полноценный CRUD для аптечки с учётом остатков, переработанная навигация (Записи только обследования, Визиты только приёмы врачей), стратегия перенесена в Аналитику, анализ производительности бандла, и исследование интеграции с Huawei Health.

**Why this approach:** Фронтенд уже на React 19 + shadcn/ui + Tailwind — редизайн идёт как доработка существующей базы. Компоненты C1-C8 атомарны и независимы: C1 (дизайн-система) — foundation для всех, остальные C2-C8 можно делать параллельно после C1. C8 (Huawei Health) — чистое исследование без кода.

**What it will NOT do:**
- НЕ трогает бэкенд (кроме добавления CRUD эндпоинтов для аптечки и визитов)
- НЕ меняет формат `data/*.md`
- НЕ ломает существующую аутентификацию и multi-bot авторизацию
- НЕ добавляет графики/тренды в аналитику (будущая итерация)
- НЕ реализует саму интеграцию с Huawei Health (только исследование)

**Effort:** Large (8 компонентов, ~42 задач, 6 волн)
**Risk:** Medium — кодовая база React уже стабильна, основные риски в объёме изменений дизайн-системы (C1) и перекрёстных зависимостях навигации
**Decisions to sanity-check:**
  1. Профиль как главная (`/` → `/profile` вместо `/records`) — меняет привычный пользователю entry point
  2. Диагнозы и аллергии выносятся на отдельные страницы (не раскрывающиеся списки)
  3. Стратегия переезжает из Профиля в Аналитику
  4. CRUD аптечки требует новых бэкенд-эндпоинтов

Your next move: approve — or run high-accuracy review via `/review-work`. Full execution detail follows below.

---

> TL;DR (machine): Large effort, Medium risk — redesign 8 components across 6 waves: design system, profile-as-main, pharmacy CRUD, records/visits restructure, analytics rethink, performance optimization, Huawei Health research. React 19 + shadcn/ui + Tailwind base is stable.

## Scope

### Must have
- [ ] C1. Глобальная дизайн-система: тёмная тема (Slate 900/800), карточки 12-16px radius, chips 9999px, segmented control, статус-пиллы без эмодзи, таблицы с 12px padding
- [ ] C2. Профиль как главная страница: аватарка с инициалами, метрики-карточки, разделы «Диагнозы» и «Аллергии» как отдельные страницы, стратегия убрана
- [ ] C3. Аптечка: CRUD лекарств (POST/PUT/DELETE /api/pharmacy/), учёт остатков +/-кнопки, days_left калькуляция, цветовая индикация (<7 красный, <14 жёлтый), секция «Постоянный приём», основа для cron-напоминаний
- [ ] C4. Записи: только обследования (Анализы, УЗИ, МРТ-КТ, Осмотры), chips-фильтры, табличный дизайн (12px padding, единицы/референсы мелким шрифтом), статусы цветом без эмодзи, ссылка на .md оригинал
- [ ] C5. Визиты: только приёмы врачей, Segmented Control (Предстоящие/Прошлые), детальный просмотр, CRUD через API
- [ ] C6. Аналитика: стратегия из Профиля перенесена, группировка ДО СТРАХОВКИ/ЕЖЕДНЕВНО/ПО СТРАХОВКЕ, заглушка под будущие графики
- [ ] C7. Производительность: анализ бандла (webpack-bundle-analyzer), оптимизация чанков React Query, удаление неиспользуемых зависимостей, lazy-loading аудит
- [ ] C8. Huawei Health: исследование API (доступность, OAuth, типы данных, регистрация, примеры запросов), документ с выводами в `Knowledge/`

### Must NOT have (guardrails, anti-slop, scope boundaries)
- ❌ НЕ трогать бэкенд кроме новых CRUD эндпоинтов (аптечка + визиты)
- ❌ НЕ менять формат `data/*.md` файлов
- ❌ НЕ ломать существующие страницы (Insurance, Fluorography)
- ❌ НЕ использовать эмодзи как статус-индикаторы (только цветовые бейджи/пиллы)
- ❌ НЕ использовать `any`, `@ts-ignore`, `as` для подавления типов
- ❌ НЕ писать самописный CSS — только Tailwind utility classes + shadcn/ui
- ❌ НЕ создавать файлы >250 LOC
- ❌ НЕ добавлять реальные графики в C6 (только структура + placeholder)
- ❌ НЕ реализовывать интеграцию с Huawei Health (только исследование C8)
- ❌ НЕ удалять работающий код без полной верификации замены

## Verification strategy
> Zero human intervention — all verification is agent-executed.
- Test decision: tests-after (vitest для хуков, ручная проверка API через curl)
- Evidence: `.omo/evidence/task-<N>-project5-redesign.<ext>`
- Build verification: `npm run build` без ошибок после каждого компонента
- TypeScript: `tsc --noEmit` strict mode без ошибок
- LSP diagnostics: чистые на всех изменённых файлах
- API smoke test: curl каждый изменённый/новый эндпоинт

## Execution strategy

### Parallel execution waves
Wave 1 (C1 — Design system, 6 задач) → Wave 2 (C2 — Profile, 7 задач) → Wave 3 (C3+C4+C5 — параллельно, 15 задач) → Wave 4 (C6 — Analytics, 5 задач) → Wave 5 (C7 — Performance, 4 задачи) → Wave 6 (C8 — Research, 5 задач)

### Dependency matrix
| Component | Depends on | Blocks | Can parallelize with |
|-----------|-----------|--------|---------------------|
| C1 - Design | — | C2-C6 (theme tokens) | — |
| C2 - Profile | C1 | C3,C4,C5 (route changes) | C3,C4,C5 (different pages) |
| C3 - Pharmacy | C1, C2 (routes) | — | C4, C5 |
| C4 - Records | C1 | — | C3, C5 |
| C5 - Visits | C1 | — | C3, C4 |
| C6 - Analytics | C1, C2 (strategy move) | — | — |
| C7 - Performance | — (after feature work) | — | — |
| C8 - Research | — (fully independent) | — | ALL (pure research) |

## Component-Specific Specifications

### C1 — Глобальная дизайн-система
> Wave 1. Foundation для всех остальных компонентов. Должен быть выполнен ПЕРВЫМ.

**Исходное состояние:** Текущие страницы используют ad-hoc инлайн-стили с `var(--tg-theme-*)`. Нет единой тёмной темы, нет системы статус-пиллов, нет стандартизированных chip-фильтров.

**Что сделать:**
- Создать `src/styles/design-tokens.css` с переменными: `--sh-bg-primary: #0F172A`, `--sh-bg-surface: #1E293B`, `--sh-text-primary: #F8FAFC`, `--sh-text-secondary: #94A3B8`, `--sh-border: rgba(255,255,255,0.08)`, `--sh-radius-card: 16px`, `--sh-radius-chip: 9999px`, `--sh-spacing-card: 16px`
- Обновить `tailwind.config.ts` — добавить кастомные цвета `sh-surface`, `sh-primary`, `sh-secondary`, `sh-border`, `sh-accent` (привязанные к Telegram CSS vars с fallback на тёмную тему)
- Создать shadcn-совместимый `StatusBadge` компонент (варианты: normal/warning/critical) — цвет шрифта + полупрозрачный фон, без эмодзи
- Создать `ChipFilter` компонент (pill-shaped, active: `#3B82F6` bg + white text, inactive: transparent + border)
- Создать `SegmentedControl` компонент (iOS-style: rounded bg с sliding active indicator)
- Удалить хардкод-цвета из `ProfilePage.tsx` (trustTierBadge, инлайн style={background/color} — заменить на StatusBadge + tailwind классы)
- Обновить `globals.css` с дизайн-токенами для светлой/тёмной темы

**Must NOT do:** Не менять Telegram WebView поведение — внутри Telegram приоритет `var(--tg-theme-*)`, вне — кастомная тёмная тема.

**Приёмка:** `npm run build` чисто. StatusBadge/ChipFilter/SegmentedControl рендерятся в сторибук-подобном тестовом компоненте. Все цвета берутся из токенов, нет инлайн-хардкода.

---

### C2 — Профиль как главная страница
> Wave 2. Меняет entry point и навигацию. Зависит от C1 (дизайн-токены).

**Исходное состояние:** `/` → `/records`. Профиль (`/profile`) показывает аватар-инициалы, метрики, expandable диагнозы и аллергии, навигацию на Препараты/Флюорографию/Стратегию.

**Что сделать:**
1. **Изменить главную:** В `routes.tsx`: `index` → `<Navigate to="/profile" replace />` (было `/records`)
2. **Аватарка:** Заменить `<User />` иконку на компонент Avatar из `patterns/mini-app-template/` (круглый, 48x48, инициалы из `full_name`, фоновый цвет из имени). Компонент скопировать адаптированно в `src/components/Avatar.tsx`
3. **Метрики-карточки:** Переработать секцию vitals — убрать `grid grid-cols-2`, сделать вертикальный `space-y-3`. Каждая карточка: surface bg (Slate 800), border-radius 16px, padding 16px. Иконка слева, сверху подпись мелким шрифтом, снизу число 24px font-weight 600. Иконки: Line Icon стиль (lucide), 1.5-2px stroke.
4. **Диагнозы → отдельная страница:** Убрать expandable секцию из ProfilePage. Вместо неё — кнопка-раздел «Диагнозы» с бейджем количества. Создать `src/features/diagnoses/` с `DiagnosesPage.tsx`. Маршрут: `/profile/diagnoses`.
5. **Аллергии → отдельная страница:** Убрать expandable секцию. Вместо неё — кнопка-раздел «Аллергии» с бейджем. Создать `src/features/allergies/` с `AllergiesPage.tsx`. Маршрут: `/profile/allergies`.
6. **Убрать стратегию:** Удалить кнопку «Стратегия здоровья» из ProfilePage (переносится в C6).
7. **Навигационная секция:** Оставить кнопки: Препараты, Флюорография, Страховка (добавить!). Все в стиле настроечных рядов (iOS Settings grouped list).

**Must NOT do:** Не удалять ProfilePage полностью — только рефакторинг. Не забыть TelegramBackButton на новых подстраницах (diagnoses, allergies).

**Приёмка:** `/` → ProfilePage. `/profile/diagnoses` → список диагнозов с StatusBadge. `/profile/allergies` → список аллергий. Кнопка «Назад» работает. Метрики отображаются в новом дизайне.

---

### C3 — Аптечка (CRUD + учёт остатков)
> Wave 3. Параллельно с C4 и C5. Требует новых бэкенд-эндпоинтов.

**Исходное состояние:** `GET /api/pharmacy/` возвращает список лекарств. `MedicationsPage.tsx` показывает карточки с name/dose/frequency/stock/days_left. Нет форм добавления/редактирования. Нет учёта остатков. Нет секции «Постоянный приём».

**Что сделать:**

**Бэкенд (новые эндпоинты):**
1. `POST /api/pharmacy/` — создать лекарство. Body: `{ name, dose, frequency, stock, prescription_expiry?, notes?, is_daily? }`
2. `PUT /api/pharmacy/{id}` — обновить. Body: partial обновления.
3. `DELETE /api/pharmacy/{id}` — удалить.
4. `POST /api/pharmacy/{id}/adjust-stock` — списать/пополнить. Body: `{ delta: number }` (отрицательное = списание, положительное = пополнение).
5. Добавить поле `is_daily: bool` и `daily_dose: int` в Medication модель (если отсутствуют).

**Фронтенд:**
1. Кнопка «+ Добавить препарат» (full-width, border-radius 12px, surface bg). Открывает Dialog (shadcn) с формой: name, dose, frequency, stock (число), daily_dose, prescription_expiry (date input), notes, is_daily (switch/toggle). Валидация: name обязателен.
2. Каждая карточка лекарства: кнопки +/- для списания/пополнения (post /adjust-stock). После изменения — оптимистичный апдейт UI + ревалидация.
3. days_left = stock / daily_dose (автоматический пересчёт при изменении stock).
4. Цветовая индикация: красный pill-badge если < 7 дней, жёлтый если 7-14, зелёный если >14.
5. prescription_expiry: если < 30 дней — оранжевый badge "Истекает".
6. Секция «Постоянный приём» — filter medications where is_daily=true, показывать отдельной группой. В будущем — cron-напоминания.
7. Кнопка «Настроить напоминания» — пока disabled, но с placeholder-текстом о будущей функциональности.

**Must NOT do:** Не ломать `GET /api/pharmacy/alerts`. Не удалять секцию supplements (БАДы) если она есть в данных.

**Приёмка:** Добавление лекарства через форму → появляется в списке. Редактирование → обновляется. Удаление → исчезает. +/- меняет stock → days_left пересчитывается. Цветовой индикатор работает. Секция «Постоянный приём» показывает только is_daily=true.

---

### C4 — Записи (только обследования + chips-фильтры)
> Wave 3. Параллельно с C3 и C5.

**Исходное состояние:** `RecordsPage.tsx` показывает категории из `GET /api/history/categories` (включает schedule, medications, терапевта). Фильтр через кнопки. Таблицы с эмодзи-статусами. Есть баг: ОАК показывается во всех категориях.

**Что сделать:**

**Бэкенд (корректировка):**
1. Исправить `GET /api/history/categories` — исключить schedule, medications, терапевт. Оставить только: Анализы, УЗИ, МРТ-КТ, Осмотры.
2. Исправить `GET /api/history/analytics?category=X` — строгая фильтрация по категории (не показывать ОАК в других категориях).

**Фронтенд:**
1. Фильтры: заменить кнопки на `ChipFilter` компонент (из C1). Активный чип: `#3B82F6` фон, белый текст. Неактивный: прозрачный + `1px solid rgba(255,255,255,0.1)`.
2. Таблицы: padding строк минимум 12px сверху и снизу (py-3). Колонки «Ед.» и «Реф.» — меньший кегль (text-xs), цвет Secondary text. Значения — обычный кегль (text-sm).
3. Статусы: убрать эмодзи (🔴🟡🟢). Использовать `StatusBadge` компонент (из C1): норма = без бейджа или серый текст, отклонение = цвет значения + полупрозрачный бейдж.
4. Ссылка «Оригинал»: иконка ExternalLink рядом с названием теста, ссылка на `_path` если доступен.

**Must NOT do:** Не показывать визиты врачей в этой секции (они в C5). Не показывать schedule/medications в категориях. Не хардкодить список категорий — всегда из API.

**Приёмка:** Категории загружаются без лишних. Chips-фильтры работают. Таблица в новом дизайне (12px padding, мелкий шрифт для Ед./Реф.). Статусы без эмодзи. ОАК не показывается в других категориях.

---

### C5 — Визиты (только приёмы + Segmented Control)
> Wave 3. Параллельно с C3 и C4.

**Исходное состояние:** `HistoryPage.tsx` показывает визиты врачей, сгруппированные по годам. Нет разделения Предстоящие/Прошлые. Нет форм CRUD.

**Что сделать:**

**Бэкенд (новый эндпоинт):**
1. `POST /api/history/visits` — создать визит. Body: `{ date, time?, doctor, institution?, purpose, status, notes?, tags? }`
2. `PUT /api/history/visits/{id}` — обновить визит.
3. `DELETE /api/history/visits/{id}` — удалить визит.

**Фронтенд:**
1. `SegmentedControl` (из C1): два таба — «Предстоящие» / «Прошлые». Активный сегмент sliding.
2. «Предстоящие»: загрузка через `GET /api/schedule/upcoming`. Карточки: doctor, date+time, institution, purpose, status badge.
3. «Прошлые»: загрузка через `GET /api/history/visits`. Карточки сгруппированы по годам. Детальный просмотр: Dialog/Sheet с полным content и recommendations.
4. Статусы через `StatusBadge`: planned = синий, pending = жёлтый, completed = зелёный, cancelled = серый.
5. Кнопка «+ Добавить визит»: Dialog с формой полей.

**Must NOT do:** Не показывать результаты обследований (они в C4). Не удалять существующую группировку по годам для прошлых визитов.

**Приёмка:** SegmentedControl переключает Предстоящие/Прошлые. Карточки с правильными статусами. Форма добавления создаёт визит. Детальный просмотр показывает content.

---

### C6 — Аналитика (стратегия + группировка)
> Wave 4. Зависит от C2 (стратегия убрана из профиля).

**Исходное состояние:** `AnalyticsPage.tsx` показывает категории + drill-down аналитику обследований. `StrategyPage.tsx` (`/strategy`) — отдельная страница со стратегией.

**Что сделать:**
1. **Объединить стратегию в Аналитику:** Удалить отдельный роут `/strategy`. Добавить стратегию как первую секцию на `AnalyticsPage`.
2. **Группировка стратегии:** `StrategyStep.section` → три группы: ДО СТРАХОВКИ, ЕЖЕДНЕВНО, ПО СТРАХОВКЕ. Каждая группа — `Card` с заголовком. Внутри — шаги с priority-бейджем, symptom, reason, what_to_say.
3. **Priority визуализация:** левый цветной border (1-2 красный, 3 жёлтый, 4-5 синий). Priority номер в маленьком круглом бейдже.
4. **Аналитика (обследования):** сохранить текущий drill-down (категория → год → запись → параметры). Перенести ВЫШЕ стратегии или ДАЛЬШЕ — стратегия первая, аналитика вторая.
5. **Placeholder для будущего:** внизу страницы — `Card` с dashed border, текст «Графики и тренды показателей — скоро».
6. **Удалить `StrategyPage.tsx`** и его роут. Обновить импорты.

**Must NOT do:** Не удалять `/api/profile/strategy` эндпоинт — он используется. Не ломать аналитику обследований.

**Приёмка:** `/analytics` показывает стратегию с группировкой ДО/ЕЖЕДНЕВНО/ПО. Ниже — аналитика обследований с drill-down. `/strategy` → 404 или редирект на `/analytics`.

---

### C7 — Производительность
> Wave 5. После всей feature-работы.

**Исходное состояние:** index.js 231KB — многовато. React.lazy используется. Кеширования API нет (каждый переход — fetch).

**Что сделать:**
1. **Bundle analysis:** Установить `rollup-plugin-visualizer` (Vite). Запустить `npm run build`, проанализировать treemap. Выявить крупные зависимости (>50KB).
2. **Code splitting:** Настроить `vite.config.ts` → `build.rollupOptions.output.manualChunks`: выделить vendor chunks (react, react-dom, shadcn, framer-motion, lucide-react, @tanstack/react-query).
3. **React Query caching:** Добавить `staleTime: 5 * 60 * 1000` (5 минут) для всех query. Добавить `gcTime: 30 * 60 * 1000` (30 минут). Профиль, стратегия, страховка, флюорография — не меняются часто → агрессивный кеш.
4. **Lazy-loading аудит:** Проверить, что все страницы используют `React.lazy`. Убедиться, что preload на hover/visible не нужен (размеры чанков <10KB).
5. **Удалить неиспользуемые зависимости:** Проверить `package.json` — удалить всё, что не импортируется.
6. **Image optimization:** Если есть иконки/изображения → убедиться что они <50KB, иначе lazy-load.

**Must NOT do:** Не ломать PWA service worker кеширование. Не менять `base: '/sh/'`.

**Приёмка:** `npm run build` выдаёт index.js < 150KB (сейчас 231KB). Vendor chunks разделены. React Query кеширует повторные запросы. Bundle analyzer report в `.omo/evidence/`.

---

### C8 — Huawei Health Research
> Wave 6. Полностью независим — чистое исследование, без кода.

**Задача:** Исследовать возможность интеграции с Huawei Health API.

**Что исследовать:**
1. **API доступность:** Huawei Health Kit API (https://developer.huawei.com/consumer/en/hms/huaweihealth/) — статус в регионе Беларусь, требования к Huawei ID/Developer Account.
2. **Типы данных:** Какие health data types доступны: heart_rate, steps, sleep, weight, blood_pressure, SpO2, exercise?
3. **Аутентификация:** OAuth 2.0 flow? API Key? Требуется ли привязка Huawei Watch/Band, или данные из Health App на телефоне?
4. **Формат:** REST API или SDK? OpenAPI спецификация доступна?
5. **Ограничения:** Rate limits, квоты, стоимость (есть ли free tier).
6. **Примеры:** Есть ли open-source реализации на GitHub (Python/Node.js), из которых можно скопировать auth flow.
7. **Альтернативы:** Apple HealthKit, Google Fit — сравнение доступности и сложности.

**Результат:** Документ `Knowledge/sasha-work/huawei-health-research.md` (в `~/WorkStation/Knowledge/`):
- Вывод: доступно/недоступно/ограничено
- Требования к регистрации
- Примеры запросов (curl)
- Оценка сложности: Low/Medium/High/Blocked
- Фидбек: стоит ли продолжать (рекомендация)

**Инструменты:** websearch (Huawei Health Kit docs), librarian (GitHub open-source примеры), context7 (Huawei SDK docs если доступны).

**Must NOT do:** Не писать код интеграции. Не регистрировать аккаунт Huawei Developer. Чисто документ.

**Приёмка:** Файл `Knowledge/sasha-work/huawei-health-research.md` существует. Содержит все 7 пунктов исследования. Содержит чёткую рекомендацию (GO / NO-GO / NEEDS_CLARIFICATION).

---

## Навигация (итоговая карта маршрутов)
> После всех компонентов:

```
/                         → redirect → /profile          (ГЛАВНАЯ — C2)
/profile                  → ProfilePage                    (аватарка, метрики, навигация — C2)
/profile/diagnoses        → DiagnosesPage                  (NEW — список диагнозов — C2)
/profile/allergies        → AllergiesPage                  (NEW — список аллергий — C2)
/profile/fluorography     → FluorographyPage               (флюорография — без изменений)
/profile/insurance        → InsurancePage                  (страховка — без изменений)
/medications              → MedicationsPage                (аптечка с CRUD — C3)
/records                  → RecordsPage                    (только обследования, chips — C4)
/history                  → HistoryPage                    (только визиты, SegmentedControl — C5)
/analytics                → AnalyticsPage                  (стратегия + аналитика — C6)
```

**Удаляемые маршруты:** `/strategy` (перенесён в `/analytics`).

## Todos
> Implementation + Test = ONE todo. Never separate.

### WAVE 1 — C1: Design System Foundation

- [ ] 1.1. `frontend/src/styles/design-tokens.css`: Создать CSS-переменные дизайн-системы для тёмной темы
  What to do: Создать файл с `:root` переменными: `--sh-bg-primary`, `--sh-bg-surface`, `--sh-text-primary`, `--sh-text-secondary`, `--sh-border`, `--sh-radius-card`, `--sh-radius-chip`, `--sh-spacing-card`, `--sh-status-normal`, `--sh-status-warning`, `--sh-status-critical`. + `.tg-theme` блок для Telegram WebView (использует `var(--tg-theme-*)`). Импортировать в `globals.css`.
  Must NOT do: Не переопределять существующие Telegram CSS vars. Не хардкодить пиксели вместо переменных.
  Parallelization: Wave 1 | Blocked by: — | Blocks: 1.2-1.6, C2-C6
  References: `.omo/prometheus-task.md:152-180 (§8 Global redesign specs)`
  Acceptance criteria: CSS variables доступны в dev tools. `body` применяет тёмную тему вне Telegram. В Telegram WebView — цвета из `var(--tg-theme-*)`.
  QA scenarios: `document.documentElement.style.getPropertyValue('--sh-bg-primary')` → `#0F172A`. Evidence: `.omo/evidence/task-1.1-project5-redesign.txt`
  Commit: Y | `feat(frontend): add dark theme CSS design tokens`

- [ ] 1.2. `frontend/tailwind.config.ts`: Обновить конфиг — кастомные цвета из дизайн-токенов
  What to do: Добавить в `theme.extend.colors`: `sh-surface`, `sh-primary`, `sh-secondary`, `sh-border`, `sh-accent`. Каждый ссылается на CSS var с fallback. Добавить `sh-radius` в `borderRadius`. Добавить `sh-spacing` в `spacing`.
  Must NOT do: Не удалять существующие shadcn/ui цвета (zinc). Не менять `content` paths.
  Parallelization: Wave 1 | Blocked by: 1.1 | Blocks: все компоненты | Can parallelize with: 1.3
  References: `frontend/tailwind.config.ts:1-30 (current config)`, `.omo/notepads/project5-v2-redesign/learnings.md:1-17 (CSS patterns)`
  Acceptance criteria: `className="bg-sh-surface text-sh-primary"` работает с Tailwind IntelliSense и в браузере.
  QA scenarios: Написать тестовый div с классами — проверка в dev tools. Evidence: `.omo/evidence/task-1.2-project5-redesign.txt`
  Commit: Y | `feat(frontend): add design tokens to Tailwind config`

- [ ] 1.3. `frontend/src/components/ui/StatusBadge.tsx`: Создать компонент статус-бейджа (без эмодзи)
  What to do: Создать компонент с вариантами: `normal` (серый текст, без фона), `warning` (жёлтый текст, полупрозрачный жёлтый фон), `critical` (красный текст, полупрозрачный красный фон). Props: `variant`, `label`, `size` (sm/lg). Высота 24px, padding 2px 8px, border-radius 12px, font-size 12px. Экспортировать через `components.json` как shadcn-совместимый.
  Must NOT do: Не использовать emoji. Не использовать встроенные shadcn Badge variants — это отдельный компонент.
  Parallelization: Wave 1 | Blocked by: — | Blocks: C2, C4, C5 | Can parallelize with: 1.2, 1.4-1.6
  References: `.omo/prometheus-task.md:167-168 (status pills spec)`, `frontend/src/features/profile/components/ProfilePage.tsx:40-49 (current trustTierBadge — удалить)`
  Acceptance criteria: `<StatusBadge variant="critical" label="Низкий запас" />` рендерит красный pill. `<StatusBadge variant="normal" label="Норма" />` — серый текст без фона.
  QA scenarios: Рендер всех трёх вариантов — сравнить с дизайн-спецификацией. Evidence: `.omo/evidence/task-1.3-project5-redesign.png`
  Commit: Y | `feat(frontend): add StatusBadge component (no emoji, color-coded)`

- [ ] 1.4. `frontend/src/components/ui/ChipFilter.tsx`: Создать компонент chips-фильтров
  What to do: Компонент принимает `items: {key, label}[]`, `selected: string`, `onSelect: (key) => void`. Рендерит горизонтальный flex-wrap ряд pill-shaped кнопок. Активный: `bg-[#3B82F6] text-white`. Неактивный: `bg-transparent border border-sh-border text-sh-secondary`. border-radius 9999px, padding 6px 16px.
  Must NOT do: Не использовать shadcn Toggle — это кастомный компонент под дизайн-спецификацию.
  Parallelization: Wave 1 | Blocked by: — | Blocks: C4 | Can parallelize with: 1.2, 1.3, 1.5, 1.6
  References: `.omo/prometheus-task.md:169 (chips filter spec)`
  Acceptance criteria: Рендерит 4 чипа, клик по второму → `onSelect` вызван с правильным key. Активный чип синий с белым текстом.
  QA scenarios: Проверить horizontal scroll при переполнении. Проверить keyboard accessibility. Evidence: `.omo/evidence/task-1.4-project5-redesign.png`
  Commit: Y | `feat(frontend): add ChipFilter component (pill-shaped category selector)`

- [ ] 1.5. `frontend/src/components/ui/SegmentedControl.tsx`: Создать компонент Segmented Control (iOS-style)
  What to do: Компонент принимает `segments: {key, label}[]`, `selected: string`, `onSelect: (key) => void`. Рендерит контейнер с закруглённым фоном (surface bg), внутри — кнопки-сегменты. Активный сегмент: скользящий фон (accent color) с `layoutId` из framer-motion для анимации. Текст активного: белый. Неактивного: secondary text. Размер: height 36px, внутренние отступы 2px.
  Must NOT do: Не использовать shadcn Tabs — это отдельный компонент.
  Parallelization: Wave 1 | Blocked by: — | Blocks: C5 | Can parallelize with: 1.2-1.4, 1.6
  References: `.omo/prometheus-task.md:170 (Segmented Control spec)`
  Acceptance criteria: 2 сегмента «Предстоящие» / «Прошлые». Переключение с анимацией sliding. Активный белый текст.
  QA scenarios: Проверить touch target size (≥44px). Проверить плавность анимации. Evidence: `.omo/evidence/task-1.5-project5-redesign.mp4`
  Commit: Y | `feat(frontend): add SegmentedControl component (iOS-style tabs)`

- [ ] 1.6. `frontend/src/`: Аудит и замена хардкод-цветов на токены во всех существующих страницах
  What to do: Пройти по всем 7 страницам + components. Заменить инлайн `style={{background: "#..."}}` и хардкодные цвета на Tailwind классы из дизайн-токенов (`bg-sh-surface`, `text-sh-primary`, `text-sh-secondary`, `border-sh-border`). Особое внимание: `ProfilePage.tsx` (trustTierBadge, vitals cards), `MedicationsPage.tsx`, `RecordsPage.tsx`.
  Must NOT do: Не менять логику. Не менять `var(--tg-theme-*)` в компонентах, которые явно работают с Telegram темой (AppShell, BottomNav).
  Parallelization: Wave 1 | Blocked by: 1.1, 1.2 | Blocks: — | Can parallelize with: 1.5
  References: Все `.tsx` файлы в `frontend/src/features/*/components/`
  Acceptance criteria: `grep -r "style={{" frontend/src/` показывает только необходимые inline-стили (не цвета). `npm run build` чисто.
  QA scenarios: Визуальный осмотр всех страниц — цвета соответствуют тёмной теме. Evidence: `.omo/evidence/task-1.6-project5-redesign.png`
  Commit: Y | `refactor(frontend): replace hardcoded colors with design tokens across all pages`

### WAVE 2 — C2: Profile as Main Page

- [ ] 2.1. `frontend/src/app/routes.tsx`: Изменить главную страницу /profile + добавить подмаршруты
  What to do:
  - `index` → `<Navigate to="/profile" replace />` (было `/records`)
  - Добавить lazy imports: `DiagnosesPage`, `AllergiesPage`
  - Добавить роуты: `/profile/diagnoses`, `/profile/allergies`
  - Удалить lazy import `StrategyPage` и роут `/strategy`
  Must NOT do: Не удалять `/records` роут. Не ломать `/profile/insurance` и `/profile/fluorography`.
  Parallelization: Wave 2 | Blocked by: — | Blocks: 2.2-2.7 | Can parallelize with: 2.2
  References: `frontend/src/app/routes.tsx:1-92 (current routes)`, `.omo/prometheus-task.md:185-196 (§9 route map)`
  Acceptance criteria: `/` → ProfilePage. `/profile/diagnoses` → 200. `/profile/allergies` → 200. `/strategy` → 404.
  QA scenarios: Перейти по каждому маршруту — проверить загрузку правильной страницы. Evidence: `.omo/evidence/task-2.1-project5-redesign.txt`
  Commit: Y | `feat(frontend): make Profile the main page, add /profile/diagnoses + /profile/allergies`

- [ ] 2.2. `frontend/src/components/Avatar.tsx`: Создать компонент аватарки с инициалами
  What to do: Скопировать/адаптировать Avatar из `patterns/mini-app-template/`. Компонент: круглый (48x48), принимает `name: string`, `size?: number`. Вычисляет инициалы (первые буквы имени и фамилии). Фоновый цвет — детерминированный из хеша имени (HSL hue). Если `photoUrl` передан — показывает изображение.
  Must NOT do: Не использовать внешние зависимости для аватара. Не хардкодить цвета — hue из хеша.
  Parallelization: Wave 2 | Blocked by: — | Blocks: — | Can parallelize with: 2.1
  References: `patterns/mini-app-template/` (Avatar component)
  Acceptance criteria: `<Avatar name="Саша Иванов" />` → круг с инициалами "СИ". Разные имена → разные цвета. `<Avatar name="Саша Иванов" photoUrl="..." />` → круг с фото.
  QA scenarios: Проверить 5 разных имён — цвета разные, инициалы правильные. Evidence: `.omo/evidence/task-2.2-project5-redesign.png`
  Commit: Y | `feat(frontend): add Avatar component with initials and color-hash`

- [ ] 2.3. `frontend/src/features/profile/components/ProfilePage.tsx`: Рефакторинг ProfilePage — аватарка, метрики-карточки, навигация
  What to do:
  - Заменить `<User />` иконку на `<Avatar name={profile.full_name} />`
  - Переработать vitals: вертикальные карточки (surface bg, 16px border-radius, 16px padding). Иконка слева, сверху подпись (text-sh-secondary, text-xs), снизу число (text-sh-primary, text-2xl, font-semibold)
  - Убрать expandable секции Диагнозов и Аллергий. Заменить на кнопки-разделы с бейджами:
    - «Диагнозы» + Badge с количеством → navigate(`/profile/diagnoses`)
    - «Аллергии» + Badge с количеством → navigate(`/profile/allergies`)
  - Убрать кнопку «Стратегия здоровья»
  - Добавить кнопку «Страховка» → navigate(`/profile/insurance`) (была только в навигации)
  - Кнопки в стиле iOS Settings grouped list (как существующие Препараты/Флюорография)
  Must NOT do: Не удалять loadData логику. Не ломать обработку ошибок (loading/error/empty).
  Parallelization: Wave 2 | Blocked by: 2.1, 2.2 | Blocks: — | Can parallelize with: 2.4, 2.5
  References: `frontend/src/features/profile/components/ProfilePage.tsx:1-325 (full current code)`, `.omo/prometheus-task.md:107-132 (§6 Profile redesign)`
  Acceptance criteria: Аватарка с инициалами. Метрики в новом дизайне (вертикальные карточки). Кнопки «Диагнозы (N)», «Аллергии (M)» с бейджами. Навигация: Препараты, Флюорография, Страховка. Кнопки «Стратегия» нет.
  QA scenarios: Открыть профиль — визуально сверить с дизайн-спецификацией. Клик «Диагнозы» → `/profile/diagnoses`. Evidence: `.omo/evidence/task-2.3-project5-redesign.png`
  Commit: Y | `feat(frontend): redesign ProfilePage — avatar, metric cards, section buttons`

- [ ] 2.4. `frontend/src/features/diagnoses/`: Создать feature + страницу для диагнозов
  What to do: Создать `src/features/diagnoses/components/DiagnosesPage.tsx`. Загрузка: `fetchProfile()` → `profile.diagnoses`. Рендер: список карточек. Каждая карточка: status + name + source + `StatusBadge` (trustTier). `TelegramBackButton` для возврата в профиль. Обработка loading/error/empty.
  Must NOT do: Не дублировать trustTierBadge логику — использовать StatusBadge из C1. Не создавать отдельный Zustand store если не нужен (данные уже в профиле).
  Parallelization: Wave 2 | Blocked by: 2.1 | Blocks: — | Can parallelize with: 2.3, 2.5, 2.6, 2.7
  References: `frontend/src/features/profile/components/ProfilePage.tsx:214-253 (current diagnoses expandable — логика для переноса)`, `frontend/src/lib/services.ts:23-25 (fetchProfile)`, `frontend/src/lib/types.ts:22-27 (DiagnosisItem)`
  Acceptance criteria: `/profile/diagnoses` показывает список диагнозов. Каждый с StatusBadge. Кнопка «Назад» работает. Loading → skeleton, error → retry, empty → «Диагнозов нет».
  QA scenarios: Переход из профиля → список диагнозов → назад. Проверить loading/error/empty. Evidence: `.omo/evidence/task-2.4-project5-redesign.png`
  Commit: Y | `feat(frontend): add DiagnosesPage with StatusBadge per diagnosis`

- [ ] 2.5. `frontend/src/features/allergies/`: Создать feature + страницу для аллергий
  What to do: Создать `src/features/allergies/components/AllergiesPage.tsx`. Загрузка: `fetchProfile()` → `profile.allergies`. Рендер: список элементов в стиле iOS grouped list (rounded card, items с border-bottom). `TelegramBackButton`. Обработка loading/error/empty.
  Must NOT do: Не дублировать логику из ProfilePage — данные из того же API.
  Parallelization: Wave 2 | Blocked by: 2.1 | Blocks: — | Can parallelize with: 2.3, 2.4, 2.6, 2.7
  References: `frontend/src/features/profile/components/ProfilePage.tsx:288-309 (current allergies expandable)`, `frontend/src/lib/services.ts:23-25 (fetchProfile)`, `frontend/src/lib/types.ts:28-33 (ProfileSchema)`
  Acceptance criteria: `/profile/allergies` показывает список строк. Кнопка «Назад» работает. Loading/error/empty обработаны.
  QA scenarios: Переход из профиля → список аллергий → назад. Пустой список → «Аллергий нет». Evidence: `.omo/evidence/task-2.5-project5-redesign.png`
  Commit: Y | `feat(frontend): add AllergiesPage as separate route`

- [ ] 2.6. `frontend/src/features/strategy/`: Удаление StrategyPage и роута
  What to do: Удалить `src/features/strategy/` целиком. Удалить lazy import и роут `/strategy` из `routes.tsx` (уже сделано в 2.1 если lazy import удалён). Убедиться что нигде нет `<Link to="/strategy">`.
  Must NOT do: Не удалять `fetchStrategy` из `services.ts` — используется в C6. Не трогать бэкенд.
  Parallelization: Wave 2 | Blocked by: 2.1 | Blocks: — | Can parallelize with: 2.3-2.5, 2.7
  References: `frontend/src/features/strategy/components/StrategyPage.tsx:1-150 (file to delete)`, `frontend/src/app/routes.tsx:14,82-89 (strategy route)`
  Acceptance criteria: `/strategy` → 404. `grep -r "StrategyPage" frontend/src/` → только C6 references (Analytics). `npm run build` чисто.
  QA scenarios: `curl /strategy` → 404. Проверить все ссылки в BottomNav и ProfilePage — нет /strategy. Evidence: `.omo/evidence/task-2.6-project5-redesign.txt`
  Commit: Y | `refactor(frontend): remove StrategyPage (moved to Analytics in C6)`

- [ ] 2.7. `frontend/src/components/nav/BottomNav.tsx`: Обновить порядок табов
  What to do: Проверить текущий порядок: Записи · Аналитика · История · Аптечка · Профиль. Если Профиль не первый — сделать первым табом. Порядок: Профиль · Записи · Аптечка · Аналитика · История. Обновить иконки: Профиль=User, Записи=ClipboardList, Аптечка=Pill, Аналитика=FlaskConical, История=Calendar.
  Must NOT do: Не добавлять новые табы (страховка, ФЛГ, диагнозы, аллергии).
  Parallelization: Wave 2 | Blocked by: — | Blocks: — | Can parallelize with: 2.3-2.6
  References: `frontend/src/components/nav/BottomNav.tsx:1-75 (current BottomNav)`
  Acceptance criteria: Первый таб — Профиль, активен при `/profile`. Порядок: Профиль · Записи · Аптечка · Аналитика · История. Все ссылки правильные.
  QA scenarios: Клик по каждому табу → правильная страница. Активный таб подсвечен. Evidence: `.omo/evidence/task-2.7-project5-redesign.png`
  Commit: Y | `feat(frontend): reorder BottomNav — Profile first, remove Strategy`

### WAVE 3 — C3, C4, C5 (PARALLEL)

#### C3 — Pharmacy CRUD

- [ ] 3.1. `app/models/medication.py` + `app/schemas/medicine.py`: Добавить поля is_daily и daily_dose
  What to do: Если отсутствуют в Pydantic модели — добавить `is_daily: bool = False` и `daily_dose: Optional[int] = None` в MedicineSchema. Обновить `from_frontmatter()` в storage если нужно.
  Must NOT do: Не менять существующие поля. Не ломать парсинг .md файлов.
  Parallelization: Wave 3 | Blocked by: — | Blocks: 3.2-3.6 | Can parallelize with: C4, C5 backend tasks
  References: `app/schemas/medicine.py:1-32 (current MedicineSchema)`, `.omo/prometheus-task.md:22-24 (§1.2 is_daily)`
  Acceptance criteria: MedicineSchema имеет is_daily (bool) и daily_dose (int|None). `GET /api/pharmacy/` возвращает эти поля.
  QA scenarios: curl GET /api/pharmacy/ → в ответе есть is_daily и daily_dose. Evidence: `.omo/evidence/task-3.1-project5-redesign.txt`
  Commit: Y | `feat(backend): add is_daily and daily_dose to Medication schema`

- [ ] 3.2. `app/routes/pharmacy.py`: Добавить POST/PUT/DELETE эндпоинты для CRUD
  What to do:
  - `POST /api/pharmacy/`: валидация через MedicineSchema, создание .md файла через MDStorage, возврат 201
  - `PUT /api/pharmacy/{id}`: загрузка существующего, обновление полей, сохранение, возврат 200
  - `DELETE /api/pharmacy/{id}`: удаление .md файла, возврат 204
  Must NOT do: Не менять GET эндпоинты. Не ломать alerts.
  Parallelization: Wave 3 | Blocked by: 3.1 | Blocks: 3.3 | Can parallelize with: C4, C5 backend tasks
  References: `app/routes/pharmacy.py:1-255 (current pharmacy routes)`, `app/storage.py` (MDStorage API)
  Acceptance criteria: POST создаёт .md файл в data/лекарства/. PUT обновляет. DELETE удаляет. Все с правильными статусами.
  QA scenarios: curl POST с валидным body → 201 + созданный объект. curl PUT с изменением → 200 + обновлённый. curl DELETE → 204. Evidence: `.omo/evidence/task-3.2-project5-redesign.txt`
  Commit: Y | `feat(backend): add CRUD endpoints for pharmacy (POST/PUT/DELETE)`

- [ ] 3.3. `app/routes/pharmacy.py`: Добавить POST /api/pharmacy/{id}/adjust-stock
  What to do: Эндпоинт принимает `{ delta: int }`. delta > 0 = пополнение, delta < 0 = списание. Обновляет `stock` в .md файле. Проверяет что stock не уходит ниже 0. Возвращает обновлённый medication.
  Must NOT do: Не позволять stock < 0. Не менять другие поля при adjust-stock.
  Parallelization: Wave 3 | Blocked by: 3.1, 3.2 | Blocks: 3.4-3.6 | Can parallelize with: C4, C5 backend tasks
  References: `app/routes/pharmacy.py:1-255`, `.omo/prometheus-task.md:27 (§1.3 stock tracking)`
  Acceptance criteria: `POST /api/pharmacy/1/adjust-stock {"delta": -2}` → stock уменьшен на 2. `{"delta": -999}` (уход в минус) → 400 error.
  QA scenarios: curl adjust-stock +5 → stock увеличился. curl adjust-stock -100 → 400. Evidence: `.omo/evidence/task-3.3-project5-redesign.txt`
  Commit: Y | `feat(backend): add adjust-stock endpoint for pharmacy`

- [ ] 3.4. `frontend/src/features/medications/components/MedicationsPage.tsx`: Кнопка «+ Добавить препарат» с Dialog-формой
  What to do: Добавить кнопку (full-width, surface bg, border-radius 12px). При клике — shadcn Dialog с формой: name (input, required), dose (input), frequency (input), stock (number), daily_dose (number), prescription_expiry (date input), notes (textarea), is_daily (Switch). Submit → `POST /api/pharmacy/`. После успеха — закрыть диалог, ревалидировать список. Обработка ошибок валидации.
  Must NOT do: Не использовать alert() для ошибок — toast или inline error.
  Parallelization: Wave 3 | Blocked by: 3.1, 3.2, 3.3, C1 | Blocks: — | Can parallelize with: 3.5, C4, C5
  References: `frontend/src/features/medications/components/MedicationsPage.tsx:1-250`, `frontend/src/components/ui/dialog.tsx`, `.omo/prometheus-task.md:16-17 (§1.1 add medication form)`
  Acceptance criteria: Кнопка «+ Добавить препарат» видна. Диалог открывается. Форма валидирует name. Submit → лекарство в списке.
  QA scenarios: Заполнить форму → submit → лекарство появилось. Оставить name пустым → ошибка валидации. Evidence: `.omo/evidence/task-3.4-project5-redesign.png`
  Commit: Y | `feat(frontend): add medication creation dialog with form validation`

- [ ] 3.5. `frontend/src/features/medications/components/MedicationsPage.tsx`: Учёт остатков (+/- кнопки, days_left, цветовая индикация)
  What to do: На каждой карточке лекарства — кнопки +/- рядом со stock. При клике → `POST adjust-stock`. Оптимистичный UI: сразу обновить stock, пересчитать days_left. Цветовой StatusBadge: days_left < 7 → critical (красный), 7-14 → warning (жёлтый), >14 → normal (зелёный). prescription_expiry < 30 дней → warning badge "Истекает".
  Must NOT do: Не блокировать UI во время API запроса. Не показывать отрицательный stock.
  Parallelization: Wave 3 | Blocked by: 3.1, 3.3, C1 | Blocks: — | Can parallelize with: 3.4, 3.6, C4, C5
  References: `.omo/prometheus-task.md:26-28 (§1.3 stock tracking + color indication)`, `frontend/src/components/ui/StatusBadge.tsx (from C1)`
  Acceptance criteria: +/- меняют stock немедленно. days_left пересчитывается. Badge красный при <7, жёлтый при 7-14, зелёный при >14. prescription_expiry badge при <30д.
  QA scenarios: Клик '-' → stock уменьшен, days_left обновлён. Проверить все цветовые пороги. Evidence: `.omo/evidence/task-3.5-project5-redesign.png`
  Commit: Y | `feat(frontend): add stock tracking with +/- buttons and color-coded days_left`

- [ ] 3.6. `frontend/src/features/medications/components/MedicationsPage.tsx`: Секция «Постоянный приём»
  What to do: Разделить список: is_daily=true → секция «Постоянный приём» с заголовком. is_daily=false → секция «Остальные препараты». Кнопка «Настроить напоминания» (disabled, с tooltip "Скоро"). Каждая карточка в секции «Постоянный приём» имеет дополнительную иконку/бейдж «Ежедневно».
  Must NOT do: Не дублировать код рендера карточек — вынести в MedicationCard компонент.
  Parallelization: Wave 3 | Blocked by: 3.1 | Blocks: — | Can parallelize with: 3.4, 3.5, C4, C5
  References: `.omo/prometheus-task.md:20-24 (§1.2 daily meds + cron)`
  Acceptance criteria: Лекарства с is_daily=true в секции «Постоянный приём». Остальные — в «Остальные». Кнопка «Настроить напоминания» disabled.
  QA scenarios: Проверить разделение при is_daily=true/false. Evidence: `.omo/evidence/task-3.6-project5-redesign.png`
  Commit: Y | `feat(frontend): separate daily medications section with reminders placeholder`

#### C4 — Records Restructure

- [ ] 4.1. `app/routes/history.py`: Исправить /api/history/categories — исключить лишние категории
  What to do: Отфильтровать categories: оставить только Анализы, УЗИ, МРТ-КТ, Осмотры. Исключить schedule, medications, терапевт, и любые другие не-обследования. Также проверить фильтрацию в /api/history/analytics — убедиться что записи строго по категории.
  Must NOT do: Не хардкодить список — фильтровать по типу данных или исключать известные не-обследования.
  Parallelization: Wave 3 | Blocked by: — | Blocks: 4.2 | Can parallelize with: C3, C5
  References: `app/routes/history.py:1-100`, `.omo/prometheus-task.md:46-48 (§2.1 remove schedule/meds from categories)`
  Acceptance criteria: `GET /api/history/categories` → не содержит "schedule", "medications", "терапевт". ОАК не показывается в категории "УЗИ".
  QA scenarios: curl categories → список без лишних. curl analytics?category=УЗИ → нет записей ОАК. Evidence: `.omo/evidence/task-4.1-project5-redesign.txt`
  Commit: Y | `fix(backend): exclude schedule/medications/therapist from history categories`

- [ ] 4.2. `frontend/src/features/records/components/RecordsPage.tsx`: Chips-фильтры + табличный дизайн
  What to do:
  - Заменить текущие кнопки фильтров на `ChipFilter` компонент (из C1)
  - Таблицы: padding строк py-3 (12px). Колонки «Ед.» и «Реф.» — `text-xs text-sh-secondary`. Значения — `text-sm`. Параметр — `text-sm font-medium`.
  - Статусы: определить `flag` из API. Если flag = "normal" или пусто → обычный текст. Если flag отклонение → `StatusBadge variant="warning"`.
  - Убрать все эмодзи (🔴🟡🟢)
  Must NOT do: Не менять drill-down логику (категория → год → запись → параметры). Не удалять ссылку «Оригинал».
  Parallelization: Wave 3 | Blocked by: 4.1, C1 | Blocks: — | Can parallelize with: C3, C5
  References: `frontend/src/features/records/components/RecordsPage.tsx:1-300`, `.omo/prometheus-task.md:55-58 (§2.3 table design + no emoji status)`
  Acceptance criteria: Chips-фильтры с анимацией. Таблицы: 12px padding, мелкий шрифт для Ед./Реф. Статусы цветом без эмодзи.
  QA scenarios: Выбрать категорию «Анализы» → таблица параметров. Проверить padding, шрифты, цвета. Evidence: `.omo/evidence/task-4.2-project5-redesign.png`
  Commit: Y | `feat(frontend): redesign RecordsPage — chip filters, table styling, no emoji`

- [ ] 4.3. `frontend/src/features/records/components/RecordsPage.tsx`: Ссылка «Оригинал» на .md файл
  What to do: Если `_path` доступен в данных записи → добавить иконку `ExternalLink` рядом с названием теста. При клике — открыть URL (в новой вкладке для десктопа, или скопировать в буфер для mobile).
  Must NOT do: Не показывать ссылку если `_path` отсутствует. Не использовать window.open без проверки.
  Parallelization: Wave 3 | Blocked by: — | Blocks: — | Can parallelize with: 4.2, C3, C5
  References: `.omo/prometheus-task.md:53 (§2.2 original .md link)`
  Acceptance criteria: Запись с `_path` показывает иконку ссылки. Клик → открывает .md (или копирует путь).
  QA scenarios: Проверить запись с _path и без. Evidence: `.omo/evidence/task-4.3-project5-redesign.png`
  Commit: Y | `feat(frontend): add original .md file link to lab records`

#### C5 — Visits Restructure

- [ ] 5.1. `app/routes/history.py`: Добавить POST/PUT/DELETE эндпоинты для визитов
  What to do: Добавить CRUD для визитов аналогично pharmacy:
  - `POST /api/history/visits` — создать визит. Body: VisitSchema поля.
  - `PUT /api/history/visits/{id}` — обновить.
  - `DELETE /api/history/visits/{id}` — удалить.
  Must NOT do: Не менять GET эндпоинты. Не ломать существующие данные.
  Parallelization: Wave 3 | Blocked by: — | Blocks: C5 | Can parallelize with: C3, C4 backend tasks
  References: `app/routes/history.py:1-100`, `app/schemas/visit.py:1-62 (VisitSchema)`
  Acceptance criteria: POST создаёт визит. PUT обновляет. DELETE удаляет. Все с правильными HTTP статусами.
  QA scenarios: curl POST/PUT/DELETE → проверить статусы и данные. Evidence: `.omo/evidence/task-5.1-project5-redesign.txt`
  Commit: Y | `feat(backend): add CRUD endpoints for visits (POST/PUT/DELETE)`

- [ ] 5.2. `frontend/src/features/history/components/HistoryPage.tsx`: SegmentedControl (Предстоящие/Прошлые)
  What to do:
  - Заменить текущую группировку по годам (или оставить для Прошлых) на SegmentedControl (из C1): «Предстоящие» / «Прошлые»
  - «Предстоящие»: `fetchUpcomingVisits()` → карточки визитов
  - «Прошлые»: `fetchVisits()` → карточки сгруппированы по годам
  - Статусы через `StatusBadge`: planned=синий, pending=жёлтый, completed=зелёный, cancelled=серый
  Must NOT do: Не терять группировку по годам для прошлых визитов. Не показывать обследования (они в C4).
  Parallelization: Wave 3 | Blocked by: C1, 5.1 | Blocks: — | Can parallelize with: 5.3, C3, C4
  References: `frontend/src/features/history/components/HistoryPage.tsx:1-200`, `.omo/prometheus-task.md:62-76 (§3 Visits redesign)`
  Acceptance criteria: SegmentedControl переключает табы. Карточки с StatusBadge. Группировка по годам для прошлых.
  QA scenarios: Переключить Предстоящие/Прошлые. Проверить статусы бейджей. Evidence: `.omo/evidence/task-5.2-project5-redesign.png`
  Commit: Y | `feat(frontend): add SegmentedControl for upcoming/past visits`

- [ ] 5.3. `frontend/src/features/history/components/HistoryPage.tsx`: Детальный просмотр + форма добавления
  What to do:
  - Клик по карточке визита → Dialog/Sheet с полным content, recommendations, _path ссылкой
  - Кнопка «+ Добавить визит» → Dialog с формой: date, time, doctor, institution, purpose, status (select), notes
  - Submit → POST /api/history/visits. Ревалидация списка.
  Must NOT do: Не дублировать форму из C3 — разные поля. Не показывать форму редактирования без необходимости.
  Parallelization: Wave 3 | Blocked by: 5.1, 5.2 | Blocks: — | Can parallelize with: C3, C4
  References: `frontend/src/features/history/components/HistoryPage.tsx:1-200`, `.omo/prometheus-task.md:69-70 (§3.2 detailed view)`
  Acceptance criteria: Клик по визиту → детальный просмотр. Кнопка «+» → форма создания. Новый визит в списке.
  QA scenarios: Создать визит → проверить в списке. Открыть детальный просмотр → контент виден. Evidence: `.omo/evidence/task-5.3-project5-redesign.png`
  Commit: Y | `feat(frontend): add visit detail view and creation form`

### WAVE 4 — C6: Analytics Rethink

- [ ] 6.1. `frontend/src/features/analytics/components/AnalyticsPage.tsx`: Интегрировать стратегию как первую секцию
  What to do: Сделать `fetchStrategy()` на mount. Рендерить стратегию первой секцией (до аналитики обследований).
  Группировка: `StrategyStep.section` → три Card-секции: «ДО СТРАХОВКИ», «ЕЖЕДНЕВНО», «ПО СТРАХОВКЕ».
  Каждый шаг: левый цветной border (priority 1-2 красный, 3 жёлтый, 4-5 синий). Priority номер в круглом бейдже. symptom, reason, what_to_say.
  Must NOT do: Не ломать аналитику обследований (категории → год → запись → параметры). Не менять API вызовы.
  Parallelization: Wave 4 | Blocked by: C1, C2 (strategy removed from profile) | Blocks: — | Can parallelize with: 6.2
  References: `frontend/src/features/analytics/components/AnalyticsPage.tsx:1-300`, `frontend/src/lib/services.ts:27-29 (fetchStrategy)`, `frontend/src/lib/types.ts:37-50 (StrategySchema)`, `.omo/prometheus-task.md:92-104 (§5 Analytics + strategy grouping)`
  Acceptance criteria: Стратегия отображается в `/analytics`. Группировка ДО/ЕЖЕДНЕВНО/ПО. priority визуализация (цветной border + бейдж). Аналитика обследований ниже.
  QA scenarios: Открыть `/analytics` → стратегия сверху. Проверить группировку. Проверить drill-down аналитики ниже. Evidence: `.omo/evidence/task-6.1-project5-redesign.png`
  Commit: Y | `feat(frontend): integrate strategy into Analytics with section grouping`

- [ ] 6.2. `frontend/src/features/analytics/components/AnalyticsPage.tsx`: Placeholder для будущих графиков
  What to do: Внизу страницы — `Card` с dashed border, padding 24px. Текст: «Графики и тренды показателей — скоро». Иконка `TrendingUp` (lucide). Серый фон, muted текст.
  Must NOT do: Не добавлять chart.js/recharts зависимости. Не писать реальную логику графиков.
  Parallelization: Wave 4 | Blocked by: — | Blocks: — | Can parallelize with: 6.1
  References: `.omo/prometheus-task.md:102-104 (§5.3 future charts)`
  Acceptance criteria: Placeholder виден внизу `/analytics`. Не добавляет новых зависимостей. `npm ls chart.js` → empty.
  QA scenarios: Открыть `/analytics`, проскроллить вниз → placeholder. Evidence: `.omo/evidence/task-6.2-project5-redesign.png`
  Commit: Y | `feat(frontend): add charts placeholder card to Analytics`

- [ ] 6.3. `frontend/src/lib/types.ts`: Удалить StrategyPage-related типы если избыточны
  What to do: Проверить что StrategySchema/StrategyStep используются ТОЛЬКО в Analytics и services. Если StrategyPage удалён — очистить неиспользуемые экспорты (если есть специфичные для старой страницы).
  Must NOT do: Не удалять StrategySchema/StrategyStep — они нужны для C6.
  Parallelization: Wave 4 | Blocked by: C2 (StrategyPage deleted) | Blocks: — | Can parallelize with: 6.1, 6.2
  References: `frontend/src/lib/types.ts:37-50 (StrategySchema)`
  Acceptance criteria: `tsc --noEmit` чисто. Нет импортов удалённых типов.
  QA scenarios: `grep -r "from.*strategy" frontend/src/` → только analytics/services. Evidence: `.omo/evidence/task-6.3-project5-redesign.txt`
  Commit: Y | `refactor(frontend): clean up Strategy types after page removal`

### WAVE 5 — C7: Performance Optimization

- [ ] 7.1. `frontend/vite.config.ts`: Настроить manualChunks для vendor splitting
  What to do: Добавить `build.rollupOptions.output.manualChunks`: `vendor-react` (react, react-dom), `vendor-shadcn` (все @radix-ui), `vendor-motion` (framer-motion), `vendor-icons` (lucide-react), `vendor-query` (@tanstack/react-query).
  Добавить `rollup-plugin-visualizer` для генерации `dist/stats.html` (treemap).
  Must NOT do: Не менять `base: '/sh/'`. Не ломать PWA плагин.
  Parallelization: Wave 5 | Blocked by: — | Blocks: — | Can parallelize with: 7.2, 7.3
  References: `frontend/vite.config.ts:1-50 (current config)`
  Acceptance criteria: `npm run build` → `dist/assets/vendor-react-*.js`, `dist/assets/vendor-shadcn-*.js`, etc. `dist/stats.html` существует.
  QA scenarios: Открыть stats.html → проверить размеры чанков. Evidence: `.omo/evidence/task-7.1-project5-redesign.html`
  Commit: Y | `perf(frontend): add vendor chunk splitting + bundle analyzer`

- [ ] 7.2. `frontend/src/app/Providers.tsx`: Настроить React Query кеширование
  What to do: В QueryClient дефолтные опции: `staleTime: 5 * 60 * 1000` (5 мин), `gcTime: 30 * 60 * 1000` (30 мин), `retry: 1`, `refetchOnWindowFocus: false`.
  Для страниц с редко меняющимися данными (профиль, стратегия, страховка, флюорография) — `staleTime: 30 * 60 * 1000` (30 мин) через query options.
  Must NOT do: Не кешировать запросы с POST/PUT/DELETE — инвалидировать после мутаций.
  Parallelization: Wave 5 | Blocked by: — | Blocks: — | Can parallelize with: 7.1, 7.3
  References: `frontend/src/app/Providers.tsx:1-50 (current Providers)`, `@tanstack/react-query` v5 docs
  Acceptance criteria: Повторный переход на страницу не вызывает fetch (данные из кеша). После мутации (POST) — fetch вызывается.
  QA scenarios: DevTools Network: зайти на Профиль → запрос. Уйти → вернуться → нет запроса. Добавить лекарство → список перезапросился. Evidence: `.omo/evidence/task-7.2-project5-redesign.txt`
  Commit: Y | `perf(frontend): configure React Query caching (5min stale, 30min gc)`

- [ ] 7.3. `frontend/package.json`: Анализ и удаление неиспользуемых зависимостей
  What to do: `npx depcheck` — найти неиспользуемые зависимости. Удалить из package.json. Проверить `npm run build` после каждого удаления.
  Must NOT do: Не удалять зависимости, используемые в конфигах (vite, tailwind, postcss, typescript, eslint). Не удалять `@telegram-apps/sdk-react`.
  Parallelization: Wave 5 | Blocked by: — | Blocks: — | Can parallelize with: 7.1, 7.2
  References: `frontend/package.json:1-50`
  Acceptance criteria: `depcheck` показывает 0 неиспользуемых зависимостей (или только false positives). `npm run build` чисто.
  QA scenarios: `npx depcheck` → report. `npm ls` → нет extraneous. Evidence: `.omo/evidence/task-7.3-project5-redesign.txt`
  Commit: Y | `chore(frontend): remove unused dependencies`

- [ ] 7.4. `frontend/`: Lazy-loading аудит
  What to do: Проверить что все 7+ страниц используют `React.lazy(() => import(...))`. Проверить что нет eager импортов в routes.tsx. Проверить что нет случайных импортов страниц в других компонентах.
  Must NOT do: Не менять структуру lazy-loading если она уже правильная.
  Parallelization: Wave 5 | Blocked by: — | Blocks: — | Can parallelize with: 7.1-7.3
  References: `frontend/src/app/routes.tsx:1-92`
  Acceptance criteria: Все страницы лениво загружены. При первом рендере грузятся только AppShell + BottomNav + главная страница.
  QA scenarios: DevTools Network: зайти на `/` → только главная страница. Перейти на `/history` → только HistoryPage чанк. Evidence: `.omo/evidence/task-7.4-project5-redesign.txt`
  Commit: Y | `perf(frontend): audit and fix lazy-loading for all pages`

### WAVE 6 — C8: Huawei Health Research

- [ ] 8.1. `Knowledge/sasha-work/huawei-health-research.md`: API доступность и требования
  What to do: Исследовать https://developer.huawei.com/consumer/en/hms/huaweihealth/ — определить статус Health Kit API. Требуется ли Huawei ID, Developer Account, верификация. Доступность в регионе Беларусь. Квоты/free tier.
  Must NOT do: Не регистрировать аккаунт. Не писать код.
  Parallelization: Wave 6 | Blocked by: — | Blocks: — | Can parallelize with: 8.2-8.5
  References: websearch "Huawei Health Kit API", "Huawei Health Kit developer registration"
  Acceptance criteria: Секция в .md: доступность API, требования к регистрации, региональные ограничения.
  QA scenarios: Проверить что информация актуальна (2025-2026). Evidence: `.omo/evidence/task-8.1-project5-redesign.md` → исследование.
  Commit: N (документ, не код)

- [ ] 8.2. Исследование: типы данных и OAuth
  What to do: Определить какие health data types доступны (heart_rate, steps, sleep, weight, SpO2, blood_pressure, exercise). Аутентификация: OAuth 2.0? API Key? Формат запросов (REST/SDK).
  Must NOT do: Не speculation — только из официальной документации.
  Parallelization: Wave 6 | Blocked by: — | Blocks: — | Can parallelize with: 8.1, 8.3-8.5
  References: websearch "Huawei Health Kit data types", Context7 "/huawei/health-kit" docs
  Acceptance criteria: Секция в .md: список доступных типов данных, схема аутентификации, примеры эндпоинтов.
  QA scenarios: Сравнить с Apple HealthKit, Google Fit — таблица сравнения. Evidence: `.omo/evidence/task-8.2-project5-redesign.md`
  Commit: N

- [ ] 8.3. Исследование: примеры реализации (open-source)
  What to do: GitHub search: "huawei health kit" Python, "huawei health" integration, "Health Kit API" example. Найти ≥2 репозитория с рабочей интеграцией. Задокументировать подходы.
  Must NOT do: Не копировать чужой код — только ссылки и описание подхода.
  Parallelization: Wave 6 | Blocked by: — | Blocks: — | Can parallelize with: 8.1, 8.2, 8.4, 8.5
  References: `grep_app_searchGitHub` "huawei health kit", librarian subagent
  Acceptance criteria: ≥2 ссылки на GitHub с кратким описанием подхода.
  QA scenarios: Проверить что репозитории не архивные (>1 года без обновлений). Evidence: `.omo/evidence/task-8.3-project5-redesign.md`
  Commit: N

- [ ] 8.4. Исследование: альтернативы (Apple Health, Google Fit)
  What to do: Сравнить Huawei Health Kit с Apple HealthKit и Google Fit по доступности в регионе, типам данных, сложности интеграции. Короткая таблица сравнения.
  Must NOT do: Не углубляться в Apple/Google — только для сравнения.
  Parallelization: Wave 6 | Blocked by: — | Blocks: — | Can parallelize with: 8.1-8.3, 8.5
  References: websearch "Apple HealthKit vs Google Fit vs Huawei Health"
  Acceptance criteria: Таблица сравнения в .md: доступность, типы данных, OAuth, сложность.
  QA scenarios: Информация непротиворечива. Evidence: `.omo/evidence/task-8.4-project5-redesign.md`
  Commit: N

- [ ] 8.5. Финальный документ: выводы и рекомендация
  What to do: Объединить результаты 8.1-8.4 в итоговый документ. Добавить секцию «Вывод»: GO (интегрировать сейчас), NO-GO (невозможно/нецелесообразно), NEEDS_CLARIFICATION (нужна доп. информация). Оценка сложности: Low/Medium/High. Рекомендация для следующего шага.
  Must NOT do: Не принимать решение без явных данных из исследования.
  Parallelization: Wave 6 | Blocked by: 8.1, 8.2, 8.3, 8.4 | Blocks: — | Can parallelize with: —
  References: `Knowledge/sasha-work/huawei-health-research.md` (создаваемый файл)
  Acceptance criteria: Документ содержит все 7 пунктов из спецификации C8. Содержит чёткую рекомендацию GO/NO-GO/NEEDS_CLARIFICATION.
  QA scenarios: Документ самодостаточен — читается без контекста исследования. Evidence: сам файл `Knowledge/sasha-work/huawei-health-research.md`
  Commit: N (документ отдельно)

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit: все 8 компонентов реализованы согласно спецификации. Проверить каждый компонент по acceptance criteria.
- [ ] F2. Code quality review: `lsp_diagnostics` чистые на всех изменённых файлах. `tsc --noEmit` strict без ошибок. `npm run build` проходит.
- [ ] F3. Real manual QA: smoke-test всех 10 маршрутов (профиль, диагнозы, аллергии, препараты, записи, визиты, аналитика, флюорография, страховка). CRUD аптечки: создать → изменить stock → удалить.
- [ ] F4. Scope fidelity: проверить что Must NOT have соблюдены (нет эмодзи-статусов, нет хардкод-цветов, бэкенд не тронут кроме CRUD, нет графиков, Huawei только документ).

## Commit strategy
- Каждый todo — атомарный коммит (conventional commits)
- Формат: `type(scope): description`
- Коммитить только после верификации (lsp_diagnostics + build)
- Wave 1-2: feature-коммиты (дизайн-система)
- Wave 3: feat(backend) + feat(frontend) раздельно
- Wave 4: feat(frontend)
- Wave 5: perf(frontend) + chore(frontend)
- Wave 6: docs(research)

## Success criteria
- [ ] Все 10 маршрутов работают, данные загружаются
- [ ] Дизайн соответствует спецификации (тёмная тема, карточки 16px, chips, segmented control, status pills без эмодзи)
- [ ] Профиль — главная страница, аватарка с инициалами
- [ ] Аптечка: полный CRUD, учёт остатков, цветовая индикация
- [ ] Записи: только обследования, табличный дизайн 12px padding
- [ ] Визиты: SegmentedControl, только приёмы врачей
- [ ] Аналитика: стратегия + аналитика в одном месте
- [ ] Бандл < 150KB, vendor chunks разделены
- [ ] Huawei Health документ с рекомендацией
- [ ] `npm run build` чисто, `lsp_diagnostics` чисто, `tsc --noEmit` чисто
