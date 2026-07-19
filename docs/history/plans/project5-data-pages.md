# План: Наполнение страниц Project5 реальными данными

> **Статус**: ready  
> **Создан**: 2026-07-04  
> **Агент**: Prometheus  
> **Исходное ТЗ**: `.omo/prometheus-task.md`

---

## Текущее состояние (аудит)

### Фронтенд
7 страниц — **все идентичные болванки** (56 строк каждая). Каждая делает `setTimeout(() => setState("data"), 300)` и рендерит `<h1>Заголовок</h1><p>... — в разработке</p>`. Ни одна не обращается к API.

### Стор (Zustand)
Только `authStore.ts` (60 строк). Feature-сторов нет. Будем создавать по мере необходимости.

### API-клиент
`api.ts` (106 строк) — готов. `apiFetch<T>(path)`, `apiPost`, `apiPut`. Авторизация через `Authorization: tma <initData>`. Возвращает типизированный JSON.

### Бэкенд (API)
Все эндпоинты готовы, работают, возвращают данные из `data/*.md`:

| Эндпоинт | Данные |
|---|---|
| `GET /api/profile/` | карточка.md (диагнозы, аллергии) |
| `GET /api/profile/strategy` | стратегия.md (план действий) |
| `GET /api/pharmacy/` | лекарства/ (список препаратов) |
| `GET /api/pharmacy/alerts` | лекарства/ (stock<7 или expiry<30д) |
| `GET /api/fluorography/` | флюорография.md (история снимков) |
| `GET /api/insurance/` | страховка.md (полисы ДМС) |
| `GET /api/history/visits` | Терапевт/ (визиты к врачу) |
| `GET /api/schedule/upcoming` | schedule/ (предстоящие визиты) |
| `GET /api/history/categories` | список категорий (Анализы, УЗИ, ...) |
| `GET /api/history/analytics?category=` | записи по категории |

### Маршруты
```
/                     → redirect → /records
/records              → RecordsPage (Записи)
/medications          → MedicationsPage (Аптечка)
/analytics            → AnalyticsPage (Аналитика)
/history              → HistoryPage (История визитов)
/profile              → ProfilePage (Профиль)
/profile/insurance    → InsurancePage (Страховка)
/profile/fluorography → FluorographyPage (Флюорография)
```

**Отсутствует**: `/strategy` — ТЗ требует отдельную страницу.

### BottomNav (5 табов)
Записи · Аналитика · История · Аптечка · Профиль

---

## Что ТЗ требует (постранично)

### 1. Профиль (`/profile`)
- Диагнозы: кнопка с бейджем (10), список с trust_tier/статус/source
- Аллергии: кнопка (3), список
- Показатели: рост/вес/ИМТ/пульс — из content блока карточки
- Кнопка перехода на `/medications`
- Кнопка флюорографии: красная если >10 мес

**API**: `GET /api/profile/` → `ProfileSchema`

### 2. Стратегия (`/strategy`) — **НОВАЯ страница**
- Разделы: ДО СТРАХОВКИ / ЕЖЕДНЕВНО / ПО СТРАХОВКЕ
- Каждый пункт: priority, symptom, reason, what_to_say

**API**: `GET /api/profile/strategy` → `StrategySchema`

### 3. Записи (`/records`)
- **BUG**: ОАК показывался везде (старый vanilla JS) — исправить при новой реализации
- Категории: Анализы, УЗИ, МРТ-КТ, Терапевт
- Ссылка «Оригинал» на .md

**API**: `GET /api/history/categories` → список категорий; `GET /api/history/analytics?category=X` → записи

### 4. Медикаменты (`/medications`)
- Список лекарств: name, dose, stock, days_left
- days_left < 7 → alert
- prescription_expiry < 30 дней → alert

**API**: `GET /api/pharmacy/` → все лекарства; `GET /api/pharmacy/alerts` → предупреждения

### 5. Флюорография (`/profile/fluorography`)
- История снимков: date, number, result, institution
- Предупреждение если >10 месяцев после последней

**API**: `GET /api/fluorography/` → `FluorographySchema`

### 6. Страховка (`/profile/insurance`)
- Активный договор: сумма/потрачено/остаток/срок
- Список полисов

**API**: `GET /api/insurance/` → `InsuranceSchema`

### 7. Визиты (`/history`)
- Предстоящие и Прошлые
- Детальный просмотр

**API**: `GET /api/history/visits` + `GET /api/schedule/upcoming`

---

## План реализации (8 волн)

### Wave 1: Типы и API-сервисы
Создать TypeScript-типы для всех API-ответов и сервисные функции.

**Файлы**:
- `frontend/src/lib/types.ts` — типы для всех API-ответов (Profile, Diagnosis, Strategy, Medication, Fluorography, Insurance, Visit, etc.)
- `frontend/src/lib/services.ts` — функции-обёртки над `apiFetch` для каждого эндпоинта

### Wave 2: Профиль (`/profile`)
Переписать `ProfilePage.tsx`:
- Загрузка с `GET /api/profile/`
- Карточка с ФИО и датой рождения
- Блок диагнозов: бейдж (10), раскрывающийся список с trust_tier/статус/source
- Блок аллергий: бейдж (3), раскрывающийся список
- Показатели из content (рост/вес/ИМТ/пульс) — парсинг текста
- Кнопка «Препараты» → `/medications`
- Кнопка «Флюорография» → красная если >10 мес

### Wave 3: Стратегия (`/strategy`) — **НОВАЯ**
Создать feature + страницу + маршрут:
- `frontend/src/features/strategy/components/StrategyPage.tsx`
- Загрузка с `GET /api/profile/strategy`
- Группировка steps по section
- Карточки с priority/symptom/reason/preparation/what_to_say
- Добавить маршрут `/strategy` в `routes.tsx`
- (Опционально) ссылка из профиля

### Wave 4: Записи (`/records`) + фикс бага
Переписать `RecordsPage.tsx`:
- Загрузка категорий с `GET /api/history/categories`
- Фильтр по категориям (Анализы, УЗИ, МРТ-КТ, Терапевт)
- Загрузка записей с `GET /api/history/analytics?category=X`
- Группировка по test_name, отображение parameters
- Ссылка «Оригинал» на .md файл (через `_path`)
- **BUG FIX**: фильтр строго по API-категории, не показывать ОАК в других категориях

### Wave 5: Медикаменты (`/medications`)
Переписать `MedicationsPage.tsx`:
- Загрузка с `GET /api/pharmacy/`
- Список: name, dose, frequency, stock, days_left
- Визуальные алерты: красный если days_left < 7, жёлтый если < 14
- prescription_expiry подсветка если < 30 дней
- Кнопка «Настроить напоминания» (плейсхолдер)

### Wave 6: Флюорография (`/profile/fluorography`)
Переписать `FluorographyPage.tsx`:
- Загрузка с `GET /api/fluorography/`
- Список снимков: date, number, result, institution
- Предупреждение: >10 мес после последней → красный баннер
- next_due дата

### Wave 7: Страховка (`/profile/insurance`)
Переписать `InsurancePage.tsx`:
- Загрузка с `GET /api/insurance/`
- Карточка с общей суммой и доступным остатком
- Список полисов: policy, sum_insured, spent, remaining, expiry
- Прогресс-бар потрачено/остаток

### Wave 8: Визиты (`/history`)
Переписать `HistoryPage.tsx`:
- Загрузка с `GET /api/history/visits` + `GET /api/schedule/upcoming`
- Два таба: Предстоящие / Прошлые
- Карточки визитов: doctor, institution, date, purpose, status
- Детальный просмотр (модалка или accordion)

---

## Правила реализации
- ✅ Только фронтенд (React + shadcn/ui + Tailwind)
- ✅ API не трогать
- ✅ Использовать `apiFetch<T>()` из `api.ts`
- ✅ Telegram-тема через CSS-переменные (`var(--tg-theme-*)`)
- ✅ Все страницы должны обрабатывать loading/error/empty/data состояния
- ✅ Использовать существующие `PageSkeleton`, `ErrorState`, `EmptyState`
- ✅ shadcn/ui компоненты для UI (Card, Badge, Button, Accordion, Tabs, etc.)

## Критерии готовности
- [ ] Все 7 страниц загружают реальные данные через API
- [ ] Каждая страница обрабатывает loading/error/empty состояния
- [ ] Фильтр категорий в Записях работает корректно (ОАК только в Анализах)
- [ ] Стратегия доступна по `/strategy`
- [ ] Флюорография показывает предупреждение при >10 мес
- [ ] `lsp_diagnostics` чисто на всех изменённых файлах
- [ ] `npm run build` проходит без ошибок
