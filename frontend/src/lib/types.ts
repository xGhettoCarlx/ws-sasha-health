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
}

export interface InsuranceSchema extends CommonBase {
  policies: InsurancePolicy[];
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
  stock: number;
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
