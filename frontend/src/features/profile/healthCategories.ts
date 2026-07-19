/**
 * Health dashboard categories by doctor specialty (Phase 2 UX rework).
 * Client-side triage: map diagnoses / visits / labs → category + color.
 */

import type { DiagnosisItem, VisitItem } from "../../lib/types";

export type TriageLevel = "green" | "yellow" | "red";

export type HealthCategoryId =
  | "cardio"
  | "gastro"
  | "dental"
  | "ent"
  | "neuro"
  | "endo"
  | "urology"
  | "ophtho"
  | "procto"
  | "ortho"
  | "therapy"
  | "derm";

export interface HealthCategoryDef {
  id: HealthCategoryId;
  /** Short UI label */
  label: string;
  /** Full specialty name */
  specialty: string;
  /** Emoji / compact glyph for circle */
  glyph: string;
  /** Keywords matched against diagnosis name/source, visit doctor/purpose/specialty */
  keywords: string[];
}

export const HEALTH_CATEGORIES: HealthCategoryDef[] = [
  {
    id: "cardio",
    label: "Кардио",
    specialty: "Кардиология",
    glyph: "❤️",
    keywords: [
      "кардио",
      "гипертон",
      "давлен",
      "сердц",
      "аритм",
      "экстрасистол",
      "экг",
      "холтер",
      "эхо-кг",
      "эхокг",
      "пульс",
    ],
  },
  {
    id: "gastro",
    label: "Гастро",
    specialty: "Гастроэнтерология",
    glyph: "🍽",
    keywords: [
      "гастро",
      "гепатоз",
      "стеатоз",
      "печень",
      "желч",
      "жильбер",
      "язвен",
      "дпк",
      "желуд",
      "подребер",
      "билирубин",
      "фгдс",
      "алт",
      "асат",
    ],
  },
  {
    id: "dental",
    label: "Стомато",
    specialty: "Стоматология",
    glyph: "🦷",
    keywords: ["стомат", "зуб", "десна", "кариес"],
  },
  {
    id: "ent",
    label: "ЛОР",
    specialty: "ЛОР",
    glyph: "👂",
    keywords: ["лор", "нос", "ринит", "синус", "глотк", "ухо", "храп", "отолар"],
  },
  {
    id: "neuro",
    label: "Невро",
    specialty: "Неврология",
    glyph: "🧠",
    keywords: [
      "неврол",
      "головн",
      "мигрен",
      "онемен",
      "ишиас",
      "мрт",
      "позвон",
      "поясниц",
    ],
  },
  {
    id: "endo",
    label: "Эндо",
    specialty: "Эндокринология",
    glyph: "🦋",
    keywords: ["эндокрин", "щитовид", "зоб", "ттг", "тирео", "узел"],
  },
  {
    id: "urology",
    label: "Уро",
    specialty: "Урология",
    glyph: "🫘",
    keywords: ["урол", "почк", "мочек", "мкб", "камень"],
  },
  {
    id: "ophtho",
    label: "Офтальмо",
    specialty: "Офтальмология",
    glyph: "👁",
    keywords: ["офтальм", "миопи", "глаз", "зрен", "пдс"],
  },
  {
    id: "procto",
    label: "Прокто",
    specialty: "Проктология",
    glyph: "🔶",
    keywords: ["прокто", "геморр"],
  },
  {
    id: "ortho",
    label: "Ортопед",
    specialty: "Ортопедия",
    glyph: "🦴",
    keywords: ["ортопед", "трохантер", "бедро", "сустав", "щёлкающ", "щелкающ"],
  },
  {
    id: "therapy",
    label: "Терапия",
    specialty: "Терапия",
    glyph: "🩺",
    keywords: ["терапевт", "воп", "кабаев", "общ"],
  },
  {
    id: "derm",
    label: "Дерма",
    specialty: "Дерматология",
    glyph: "✨",
    keywords: ["дермат", "кож", "сып", "зуд"],
  },
];

export const TRIAGE_COLORS: Record<
  TriageLevel,
  { ring: string; bg: string; text: string; label: string }
> = {
  green: {
    ring: "#34C759",
    bg: "rgba(52,199,89,0.12)",
    text: "#248A3D",
    label: "спокойно",
  },
  yellow: {
    ring: "#FF9500",
    bg: "rgba(255,149,0,0.14)",
    text: "#C93400",
    label: "контроль",
  },
  red: {
    ring: "#FF3B30",
    bg: "rgba(255,59,48,0.12)",
    text: "#D70015",
    label: "срочно",
  },
};

function blobOf(...parts: Array<string | null | undefined>): string {
  return parts
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .replace(/ё/g, "е");
}

export function matchCategoryId(text: string): HealthCategoryId | null {
  const b = text.toLowerCase().replace(/ё/g, "е");
  for (const cat of HEALTH_CATEGORIES) {
    if (cat.keywords.some((k) => b.includes(k))) return cat.id;
  }
  return null;
}

function diagnosisTriage(status?: string): TriageLevel {
  if (!status) return "yellow";
  if (status.includes("🔴") || /срочно|active|актив/i.test(status)) return "red";
  if (status.includes("🟡") || /контроль|вопрос/i.test(status)) return "yellow";
  if (status.includes("🟢") || status.includes("✅") || /ремисс|фон|ok/i.test(status))
    return "green";
  return "yellow";
}

function maxTriage(a: TriageLevel, b: TriageLevel): TriageLevel {
  const rank = { green: 0, yellow: 1, red: 2 } as const;
  return rank[a] >= rank[b] ? a : b;
}

export interface CategoryDiagnosis {
  name: string;
  status?: string;
  date?: string;
  source?: string | null;
  triage: TriageLevel;
}

export interface CategoryVisit {
  id?: string;
  title: string;
  date?: string | null;
  time?: string | null;
  doctor?: string;
  institution?: string | null;
  status?: string;
  purpose?: string;
  future: boolean;
}

export interface CategoryBucket {
  def: HealthCategoryDef;
  triage: TriageLevel;
  diagnoses: CategoryDiagnosis[];
  futureVisits: CategoryVisit[];
  pastVisits: CategoryVisit[];
  /** Free-form lab / imaging notes derived from sources */
  studies: string[];
}

function visitToItem(v: VisitItem, future: boolean): CategoryVisit {
  const title =
    v.title ||
    v.purpose ||
    v.doctor ||
    v.specialty ||
    "Визит";
  return {
    id: v.id,
    title,
    date: v.effective_date || v.visit_date || v.date,
    time: v.time,
    doctor: v.doctor,
    institution: v.institution,
    status: v.status,
    purpose: v.purpose,
    future,
  };
}

function isFutureVisit(item: VisitItem, todayIso: string): boolean {
  if (item.status === "completed" || item.status === "cancelled") return false;
  const raw = item.effective_date || item.visit_date || item.date || "";
  if (!raw) {
    return (
      item.status === "planned" ||
      item.status === "pending" ||
      item.status === "draft" ||
      item.status === "booked"
    );
  }
  return raw.slice(0, 10) >= todayIso.slice(0, 10);
}

export function buildCategoryBuckets(input: {
  diagnoses: DiagnosisItem[] | Array<Record<string, unknown>>;
  visits: VisitItem[];
  todayIso?: string;
}): CategoryBucket[] {
  const today = (input.todayIso || new Date().toISOString()).slice(0, 10);
  const buckets = new Map<HealthCategoryId, CategoryBucket>();

  for (const def of HEALTH_CATEGORIES) {
    buckets.set(def.id, {
      def,
      triage: "green",
      diagnoses: [],
      futureVisits: [],
      pastVisits: [],
      studies: [],
    });
  }

  for (const raw of input.diagnoses) {
    const d = raw as DiagnosisItem & { name?: string; content?: string };
    const name = d.name || "";
    const source = d.source || d.content || "";
    const id = matchCategoryId(blobOf(name, source, d.status));
    if (!id) continue;
    const b = buckets.get(id)!;
    const triage = diagnosisTriage(d.status);
    b.diagnoses.push({
      name,
      status: d.status,
      date: d.date,
      source: source || null,
      triage,
    });
    b.triage = maxTriage(b.triage, triage);
    // Surface imaging/labs mentioned in diagnosis source
    if (/узи|экг|холтер|мрт|кт|анализ|оак|биохим|фгдс/i.test(String(source))) {
      const note = String(source).trim();
      if (note && !b.studies.includes(note)) b.studies.push(note);
    }
  }

  for (const v of input.visits) {
    const id = matchCategoryId(
      blobOf(v.specialty, v.doctor, v.purpose, v.title, v.notes, ...(v.tags || [])),
    );
    if (!id) continue;
    const b = buckets.get(id)!;
    const future = isFutureVisit(v, today);
    const item = visitToItem(v, future);
    if (future) {
      b.futureVisits.push(item);
      // Open visits elevate attention at least to yellow
      b.triage = maxTriage(b.triage, "yellow");
    } else {
      b.pastVisits.push(item);
    }
  }

  // Sort: red → yellow → green, then by activity count
  const list = Array.from(buckets.values());
  const rank = { red: 0, yellow: 1, green: 2 } as const;
  list.sort((a, b) => {
    const tr = rank[a.triage] - rank[b.triage];
    if (tr !== 0) return tr;
    const actA =
      a.diagnoses.length + a.futureVisits.length + a.pastVisits.length;
    const actB =
      b.diagnoses.length + b.futureVisits.length + b.pastVisits.length;
    return actB - actA;
  });

  return list;
}

export function getCategoryById(id: string): HealthCategoryDef | undefined {
  return HEALTH_CATEGORIES.find((c) => c.id === id);
}
