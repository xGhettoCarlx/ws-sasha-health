# Sasha Health Frontend — Apple HIG Prototype

**Version:** `3.0.0-apple-hig`  
**Stack:** React 19 · TypeScript · Vite 6 · Tailwind CSS 4

## Design system

Airy **Apple Human Interface Guidelines** look:

- System font stack (`-apple-system` / SF Pro)
- Grouped background `#F2F2F7`, white cards, soft shadows
- Glassmorphism nav/cards (`backdrop-filter: blur`)
- Large titles, generous spacing, 20–28px radii
- Apple Health accents (pink heart, blue activity, green nutrition…)

### Key folders

```text
src/
  styles/           # design-tokens.css + globals.css
  components/apple/ # GlassCard, MetricCard, charts, ListGroup
  lib/mock-data.ts  # realistic medical demo data
  features/*/       # page screens
```

## Demo mode

By default `DEMO_MODE` is **on** (`VITE_DEMO_MODE` not `false`):

- Auto-login as demo user in the browser
- All main screens render with mock medical data (no API required)

```bash
npm ci
npm run dev    # http://localhost:5173/sh/
npm run build
```

Set `VITE_DEMO_MODE=false` to require real auth/API.

## Screens

| Route | Content |
|-------|---------|
| `/dashboard` | Activity rings, vitals grid, BP chart, visit, daily plan |
| `/medications` | Stock bars, filters, low-stock alert |
| `/records` | Visits + lab results with parameter rows |
| `/history` | ALT trend bar chart + study list |
| `/strategy` | Daily checklist + priorities |
| `/profile` | Patient card, diagnoses, allergies, DMC card |
