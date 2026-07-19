/**
 * Real-data navigator API (BP/weight, checkups, complaints, previsit).
 */
import { apiFetch, apiPost } from "./api";

export interface OverviewResponse {
  patient: {
    full_name?: string;
    short_name?: string;
    birth_date?: string;
    diagnoses: unknown[];
    allergies: string[];
    summary_line?: string;
  };
  vitals: {
    last_bp?: { bp?: string; date?: string } | null;
    last_weight?: {
      weight_kg?: number;
      date?: string | null;
      source?: string;
    } | null;
    bp_count: number;
    weight_count: number;
  };
  checkups: {
    total: number;
    overdue: number;
    items: CheckupItem[];
  };
  complaints_open: number;
  insurance?: Record<string, unknown> | null;
  disclaimer: string;
}

export interface CheckupItem {
  id: string;
  name: string;
  interval: string;
  last_date?: string | null;
  status: "ok" | "plan" | "overdue" | string;
  status_label: string;
  due_in_days?: number | null;
}

export interface ComplaintItem {
  id: string;
  date: string;
  text: string;
  severity: number;
  specialty_hint?: string | null;
  tags?: string[];
  resolved?: boolean;
  navigator?: {
    specialty: string;
    covered: boolean | string;
    note: string;
    score: number;
  }[];
}

export interface NavRoute {
  specialty: string;
  score: number;
  covered: boolean | string;
  note: string;
  prep: string[];
}

export function fetchOverview(): Promise<OverviewResponse> {
  return apiFetch<OverviewResponse>("/api/overview");
}

export function fetchVitals(limit = 60) {
  return apiFetch<{ count: number; items: unknown[]; tracked: string[] }>(
    `/api/vitals?limit=${limit}`,
  );
}

export function postVital(data: {
  bp?: string;
  weight_kg?: number;
  notes?: string;
  when?: string;
}) {
  return apiPost<{ ok: boolean }>("/api/vitals", data);
}

export function fetchCheckups() {
  return apiFetch<{
    count: number;
    summary: { ok: number; plan: number; overdue: number };
    items: CheckupItem[];
  }>("/api/checkups");
}

export function fetchComplaints(includeResolved = false) {
  return apiFetch<{ count: number; items: ComplaintItem[] }>(
    `/api/complaints?include_resolved=${includeResolved}`,
  );
}

export function postComplaint(data: {
  text: string;
  severity?: number;
  specialty_hint?: string;
  tags?: string[];
}) {
  return apiPost<ComplaintItem>("/api/complaints", data);
}

export async function resolveComplaint(id: string, hard = false) {
  return apiFetch<{ ok: boolean }>(
    `/api/complaints/${id}?hard=${hard}`,
    { method: "DELETE" },
  );
}

export function fetchNavigator(q?: string) {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  return apiFetch<{
    routes: NavRoute[];
    insurance: {
      policies: unknown[];
      not_covered: string[];
      body_excerpt?: string;
    };
    open_complaints: number;
  }>(`/api/navigator${qs}`);
}

export function postPrevisit(data: {
  specialty: string;
  doctor?: string;
  institution?: string;
  include_abnormal_labs?: boolean;
  include_open_complaints?: boolean;
}) {
  return apiPost<{
    specialty: string;
    prompt: string;
    meta: {
      complaints_used: number;
      labs_used: number;
      zero_api: boolean;
      hint: string;
    };
  }>("/api/previsit", data);
}
