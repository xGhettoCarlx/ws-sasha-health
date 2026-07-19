/**
 * TypeScript types mirroring Python Pydantic schemas for Sasha Health API.
 *
 * All field names use snake_case to match JSON responses from FastAPI.
 */

// ─── Common ───────────────────────────────────────────────────────────────

export type TrustTier = "unverified" | "verified" | "trusted";

export interface CommonBase {
  id?: string | null;
  trust_tier: TrustTier;
  tags: string[];
  date: string;
  source?: string | null;
  content?: string | null;
}

// ─── Profile ──────────────────────────────────────────────────────────────

export interface DiagnosisItem extends CommonBase {
  status: string;
  name: string;
  source?: string | null;
}

export interface ProfileSchema extends CommonBase {
  full_name: string;
  birth_date: string;
  diagnoses: DiagnosisItem[];
  allergies: string[];
}

// ─── Strategy ─────────────────────────────────────────────────────────────

export interface StrategyStep extends CommonBase {
  section: string;
  priority: number;
  symptom?: string | null;
  reason?: string | null;
  preparation?: string | null;
  what_to_say?: string | null;
}

export interface StrategySchema extends CommonBase {
  title: string;
  steps: StrategyStep[];
  updated: string;
}

// ─── Insurance ────────────────────────────────────────────────────────────

export interface InsurancePolicy extends CommonBase {
  policy: string;
  sum_insured: number;
  spent: number;
  remaining: number;
  expiry?: string | null;
  premium?: number | null;
  insurer?: string | null;
  program?: string | null;
  policyholder?: string | null;
}

export interface InsuranceSchema extends CommonBase {
  policies: InsurancePolicy[];
  content?: string | null;
}

// ─── Fluorography ─────────────────────────────────────────────────────────

export interface FluorographyRecord {
  date: string;
  number: string;
  result: string;
  institution: string;
}

export interface FluorographySchema {
  history: FluorographyRecord[];
  next_due?: string | null;
}

// ─── Medications (Pharmacy) ───────────────────────────────────────────────

export interface Medication {
  id: number;
  name: string;
  dose: string;
  frequency: string;
  /** Agent files use "63 таб"; API may also return stock_count. */
  stock: number | string | null;
  stock_count?: number;
  prescription_expiry?: string | null;
  notes?: string | null;
  days_left?: number | null;
  daily_dose?: number | null;
  is_daily?: boolean;
  owner_name?: string;
}

// ─── Visits (History) ─────────────────────────────────────────────────────

export type VisitStatus = "planned" | "pending" | "completed" | "cancelled";

export interface VisitRecord {
  date: string;
  time?: string | null;
  doctor: string;
  institution?: string | null;
  purpose: string;
  complaint?: string | null;
  status: VisitStatus;
  notes?: string | null;
  content?: string | null;
  _path?: string;
  _bundle?: string;
}

export interface VisitsResponse {
  count: number;
  items: VisitRecord[];
}

export interface UpcomingVisitsResponse {
  visits: VisitItem[];
}

export interface VisitItem {
  id?: string;
  date: string;
  time?: string | null;
  doctor: string;
  institution?: string | null;
  purpose: string;
  status: VisitStatus;
  notes?: string | null;
  tags?: string[];
  pipeline_stage?: number | null;
  specialty?: string | null;
  visit_date?: string | null;
  insurance_warned?: boolean;
  pipeline_cycle?: string | null;
  effective_date?: string | null;
  kind?: string;
  title?: string;
  source?: string;
  category?: string;
}

// ─── Pipeline / Timeline / Trojan ─────────────────────────────────────────

export type PipelineStageStatus = "done" | "active" | "empty";

export interface PipelineStage {
  stage: number;
  key: string;
  title: string;
  goal: string;
  icon: string;
  color: string;
  visits: VisitItem[];
  counts: { total: number; completed: number; open: number };
  status: PipelineStageStatus;
}

export interface PipelineResponse {
  stages: PipelineStage[];
  active_stage: number;
  total_visits: number;
  summary: {
    open: number;
    completed: number;
    insurance_warned: number;
    insurance_pending: number;
  };
}

export interface TimelineMonthGroup {
  month: string;
  label: string;
  items: VisitItem[];
}

export interface TimelineYearGroup {
  year: string;
  months: TimelineMonthGroup[];
}

export interface TimelineResponse {
  today: string;
  future: VisitItem[];
  past: {
    groups: TimelineYearGroup[];
    undated: VisitItem[];
    count: number;
  };
  counts: {
    future: number;
    past: number;
    insurance_unwarned_future: number;
  };
}

export interface TrojanBooster {
  id: string;
  text: string;
  rationale: string;
}

export interface TrojanComplaint {
  id: string;
  text: string;
  severity?: number;
  specialty_hint?: string;
  date?: string;
  tags?: string[];
}

export interface TrojanResponse {
  specialty: string;
  specialties: string[];
  boosters: TrojanBooster[];
  boosters_by_specialty: Record<string, TrojanBooster[]>;
  complaints: TrojanComplaint[];
  selected_complaint_ids: string[];
  selected_booster_ids: string[];
  notes: string;
  updated?: string;
}

export interface TrojanComposeResponse {
  specialty: string;
  script: string;
  real_count: number;
  booster_count: number;
  mix_ok: boolean;
}

// ─── Analytics / History ─────────────────────────────────────────────────

export interface AnalyticsParameter {
  date: string;
  test_name: string;
  parameter: string;
  value: string;
  unit?: string | null;
  ref_range?: string | null;
  flag?: string | null;
}

export interface AnalyticsResponse {
  count: number;
  items: AnalyticsParameter[];
}

export interface CategoriesResponse {
  categories: string[];
}

// ─── Admin ─────────────────────────────────────────────────────────────

export interface PendingUser {
  telegram_id: number;
  first_name?: string | null;
  timestamp: string;
}

export interface PendingList {
  count: number;
  users: PendingUser[];
}

export interface ApproveRequest {
  telegram_id: number;
  first_name: string;
  last_name: string;
  family: string;
  home: string;
  bot_token: string;
}

export interface ApproveResponse {
  status: string;
  telegram_id: number;
  household_entry: string;
}

// ─── Quick Journal Records ─────────────────────────────────────────────

export interface QuickRecord {
  date: string;
  bp?: string | null;
  weight_kg?: number | null;
  /** @deprecated not shown in UI */
  pulse?: number | null;
  notes?: string | null;
  tags?: string[];
  trust_tier?: string;
}
