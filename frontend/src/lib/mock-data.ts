/**
 * Realistic medical mock data for Apple-style UI evaluation.
 * Used when API is unavailable or DEMO mode is active.
 */

/** Demo mock UI is OFF by default — real agent files via FastAPI. */
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

export interface MockVital {
  id: string;
  label: string;
  value: string;
  unit: string;
  accent: string;
  trend: "up" | "down" | "stable";
  trendLabel: string;
  history: number[];
}

export interface MockMedication {
  id: number;
  name: string;
  dose: string;
  frequency: string;
  stock: number;
  days_left: number;
  is_daily: boolean;
  notes?: string;
  color: string;
}

export interface MockVisit {
  id: string;
  date: string;
  time?: string;
  doctor: string;
  specialty: string;
  institution: string;
  purpose: string;
  status: "planned" | "completed" | "cancelled";
}

export interface MockLab {
  id: string;
  date: string;
  name: string;
  category: string;
  status: "normal" | "attention" | "critical";
  summary: string;
  params: { name: string; value: string; unit: string; flag?: "high" | "low" | "ok" }[];
}

export interface MockDiagnosis {
  id: string;
  name: string;
  status: "active" | "watch" | "remission" | "resolved";
  statusEmoji: string;
  source: string;
  date: string;
}

export const mockPatient = {
  full_name: "Калинов Александр Игоревич",
  short_name: "Александр",
  birth_date: "1993-08-26",
  age: 32,
  blood_type: "A(II) Rh+",
  height_cm: 182,
  weight_kg: 94,
  bmi: 28.4,
  avatar_initials: "АК",
};

/** Only BP + weight remain — pulse/SpO2/temp/steps/sleep removed from product. */
export const mockVitals: MockVital[] = [
  {
    id: "bp",
    label: "Давление",
    value: "128/82",
    unit: "мм рт.ст.",
    accent: "#FF2D55",
    trend: "down",
    trendLabel: "утро/вечер",
    history: [142, 138, 135, 132, 130, 129, 128],
  },
  {
    id: "weight",
    label: "Вес",
    value: "100",
    unit: "кг",
    accent: "#34C759",
    trend: "stable",
    trendLabel: "из карточки",
    history: [100, 100, 100, 100, 100, 100, 100],
  },
];

export const mockMedications: MockMedication[] = [
  {
    id: 1,
    name: "Магний (Mg)",
    dose: "200 мг",
    frequency: "на ночь",
    stock: 63,
    days_left: 60,
    is_daily: true,
    notes: "Помогает при экстрасистолах",
    color: "#5856D6",
  },
  {
    id: 2,
    name: "Аэртал",
    dose: "100 мг",
    frequency: "по необходимости",
    stock: 12,
    days_left: 8,
    is_daily: false,
    notes: "При боли в спине",
    color: "#FF9500",
  },
  {
    id: 3,
    name: "Парлазин",
    dose: "5 мг",
    frequency: "вечером при аллергии",
    stock: 28,
    days_left: 28,
    is_daily: false,
    notes: "Сезонный контроль",
    color: "#34C759",
  },
  {
    id: 4,
    name: "Омепразол",
    dose: "20 мг",
    frequency: "утром натощак",
    stock: 18,
    days_left: 18,
    is_daily: true,
    notes: "Гастропротекция",
    color: "#007AFF",
  },
];

export const mockVisits: MockVisit[] = [
  {
    id: "v1",
    date: "2026-07-22",
    time: "10:30",
    doctor: "Спицарева Е.В.",
    specialty: "Кардиология",
    institution: "РКМЦ",
    purpose: "Контроль АД, ЭКГ",
    status: "planned",
  },
  {
    id: "v2",
    date: "2026-08-05",
    time: "14:00",
    doctor: "Ставская М.А.",
    specialty: "ЛОР",
    institution: "Поликлиника №3",
    purpose: "Пост-ринит контроль",
    status: "planned",
  },
  {
    id: "v3",
    date: "2026-06-10",
    time: "09:15",
    doctor: "Кабаев А.С.",
    specialty: "Терапия",
    institution: "Клиника «МедЭксперт»",
    purpose: "Осмотр, направление на ОАК",
    status: "completed",
  },
  {
    id: "v4",
    date: "2026-05-18",
    doctor: "Иванова Н.П.",
    specialty: "Гастроэнтерология",
    institution: "РКМЦ",
    purpose: "УЗИ брюшной полости",
    status: "completed",
  },
];

export const mockLabs: MockLab[] = [
  {
    id: "lab1",
    date: "2026-06-10",
    name: "Общий анализ крови",
    category: "Анализы",
    status: "attention",
    summary: "Лейкоциты слегка повышены",
    params: [
      { name: "Гемоглобин", value: "148", unit: "г/л", flag: "ok" },
      { name: "Эритроциты", value: "4.9", unit: "×10¹²/л", flag: "ok" },
      { name: "Лейкоциты", value: "11.2", unit: "×10⁹/л", flag: "high" },
      { name: "Тромбоциты", value: "245", unit: "×10⁹/л", flag: "ok" },
      { name: "СОЭ", value: "12", unit: "мм/ч", flag: "ok" },
    ],
  },
  {
    id: "lab2",
    date: "2026-06-10",
    name: "Биохимия крови",
    category: "Анализы",
    status: "attention",
    summary: "Билирубин и АЛТ на верхней границе",
    params: [
      { name: "Глюкоза", value: "5.4", unit: "ммоль/л", flag: "ok" },
      { name: "АЛТ", value: "52", unit: "Ед/л", flag: "high" },
      { name: "АСТ", value: "38", unit: "Ед/л", flag: "ok" },
      { name: "Билирубин общ.", value: "24", unit: "мкмоль/л", flag: "high" },
      { name: "Креатинин", value: "88", unit: "мкмоль/л", flag: "ok" },
      { name: "Холестерин", value: "5.8", unit: "ммоль/л", flag: "high" },
    ],
  },
  {
    id: "lab3",
    date: "2025-10-10",
    name: "УЗИ щитовидной железы",
    category: "УЗИ",
    status: "normal",
    summary: "Структура без очаговых изменений",
    params: [
      { name: "Объём пр. доли", value: "7.2", unit: "мл", flag: "ok" },
      { name: "Объём лев. доли", value: "6.8", unit: "мл", flag: "ok" },
    ],
  },
  {
    id: "lab4",
    date: "2024-01-06",
    name: "УЗИ брюшной полости",
    category: "УЗИ",
    status: "attention",
    summary: "Признаки стеатоза, S-перегиб ЖП",
    params: [
      { name: "Печень", value: "стеатоз", unit: "", flag: "high" },
      { name: "Камень почки", value: "3.5", unit: "мм", flag: "high" },
    ],
  },
];

export const mockDiagnoses: MockDiagnosis[] = [
  {
    id: "d1",
    name: "Гипертоническая болезнь 2 ст., риск 2",
    status: "active",
    statusEmoji: "🔴",
    source: "ЭКГ 22.01.2026 + осмотр Кабаев 10.06.2026",
    date: "2026-06-10",
  },
  {
    id: "d2",
    name: "Жировой гепатоз + стеатоз печени",
    status: "active",
    statusEmoji: "🔴",
    source: "УЗИ брюшной полости 06.01.2024",
    date: "2024-01-06",
  },
  {
    id: "d3",
    name: "Синдром Жильбера (под вопросом)",
    status: "watch",
    statusEmoji: "🟡",
    source: "Билирубин ↑, Кабаев 10.06.2026",
    date: "2026-06-10",
  },
  {
    id: "d4",
    name: "Язвенная болезнь луковицы ДПК",
    status: "remission",
    statusEmoji: "🟡",
    source: "Кабаев 10.06.2026",
    date: "2026-06-10",
  },
  {
    id: "d5",
    name: "Мочекаменная болезнь (камень 3.5 мм)",
    status: "resolved",
    statusEmoji: "✅",
    source: "УЗИ 06.01.2024",
    date: "2024-01-06",
  },
];

export const mockAllergies = ["Пенициллин (сыпь)", "Пыльца берёзы (сезон)", "Аспирин — осторожно"];

export const mockInsurance = {
  policy: "ДМС «Здоровье+» №4821-26",
  insurer: "Белгосстрах",
  sum_insured: 37651.83,
  spent: 8420.5,
  remaining: 29231.33,
  expiry: "2027-01-24",
  coverage: ["Поликлиника", "Диагностика", "Стоматология (лимит)", "Стационар"],
};

export const mockStrategy = {
  title: "Стратегия 2026 — контроль АД и печени",
  updated: "2026-07-06",
  daily: [
    "Давление утром и вечером, запись в дневник",
    "Магний 200 мг на ночь",
    "Омепразол 20 мг утром натощак",
    "Ходьба ≥ 7 000 шагов",
    "Ужин без жареного, ограничить алкоголь",
  ],
  priorities: [
    {
      title: "Кардиология",
      detail: "Контроль АД, холтер при необходимости, ЭКГ на визите 22.07",
      priority: 1,
    },
    {
      title: "Гепатология / УЗИ",
      detail: "Повтор УЗИ печени через 6 мес, снизить вес на 5–7%",
      priority: 2,
    },
    {
      title: "Лаборатория",
      detail: "Повтор билирубин, АЛТ, липиды в августе",
      priority: 3,
    },
  ],
};

export const mockFluorography = {
  last_date: "2025-11-12",
  number: "ФЛ-2025-11842",
  result: "Без патологических изменений",
  institution: "ГП №12",
  next_due: "2026-11-12",
};

export const mockInbox = [
  {
    id: "in1",
    title: "Скан биохимии 10.06",
    status: "pending" as const,
    date: "2026-07-05",
    preview: "Ожидает проверки OCR",
  },
  {
    id: "in2",
    title: "Направление к кардиологу",
    status: "verified" as const,
    date: "2026-06-11",
    preview: "Добавлено в расписание",
  },
];

export const mockDailyActivity = {
  move: 420,
  moveGoal: 500,
  exercise: 28,
  exerciseGoal: 30,
  stand: 10,
  standGoal: 12,
};

/** BP readings for chart (last 14 days) */
export const mockBpSeries = [
  { day: "3", sys: 138, dia: 88 },
  { day: "4", sys: 136, dia: 86 },
  { day: "5", sys: 140, dia: 90 },
  { day: "6", sys: 134, dia: 84 },
  { day: "7", sys: 132, dia: 84 },
  { day: "8", sys: 130, dia: 82 },
  { day: "9", sys: 131, dia: 83 },
  { day: "10", sys: 129, dia: 82 },
  { day: "11", sys: 128, dia: 80 },
  { day: "12", sys: 130, dia: 81 },
  { day: "13", sys: 127, dia: 80 },
  { day: "14", sys: 128, dia: 82 },
  { day: "15", sys: 126, dia: 80 },
  { day: "16", sys: 128, dia: 82 },
];
