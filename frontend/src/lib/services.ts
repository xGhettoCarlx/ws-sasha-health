/**
 * Typed API service functions for Sasha Health.
 *
 * Each function wraps apiFetch with correct return types matching
 * the backend Pydantic schemas.
 */

import { apiDelete, apiFetch, apiFetchBlob, apiPost, apiPut } from "./api";
import type {
  AnalyticsResponse,
  ApproveRequest,
  ApproveResponse,
  CategoriesResponse,
  FluorographySchema,
  InsuranceSchema,
  Medication,
  PendingList,
  PipelineResponse,
  ProfileSchema,
  QuickRecord,
  StrategySchema,
  TimelineResponse,
  TrojanComposeResponse,
  TrojanResponse,
  UpcomingVisitsResponse,
  VisitItem,
  VisitsResponse,
} from "./types";

// ─── Profile ──────────────────────────────────────────────────────────────

export function fetchProfile(): Promise<ProfileSchema> {
  return apiFetch<ProfileSchema>("/api/profile/");
}

export function fetchStrategy(): Promise<StrategySchema> {
  return apiFetch<StrategySchema>("/api/profile/strategy");
}

// ─── Pharmacy / Medications ───────────────────────────────────────────────

export function fetchMedications(): Promise<Medication[]> {
  return apiFetch<Medication[]>("/api/pharmacy/");
}

export function fetchMedicationAlerts(): Promise<Medication[]> {
  return apiFetch<Medication[]>("/api/pharmacy/alerts");
}

export function createMedication(data: Partial<Medication>): Promise<Medication> {
  return apiPost<Medication>("/api/pharmacy/", data);
}

export function updateMedication(id: number, data: Partial<Medication>): Promise<Medication> {
  return apiPut<Medication>(`/api/pharmacy/${id}`, data);
}

export function deleteMedication(id: number): Promise<void> {
  return apiDelete<void>(`/api/pharmacy/${id}`);
}

export function adjustMedicationStock(id: number, delta: number): Promise<Medication> {
  return apiPost<Medication>(`/api/pharmacy/${id}/adjust-stock`, { delta });
}

// ─── Fluorography ─────────────────────────────────────────────────────────

export function fetchFluorography(): Promise<FluorographySchema> {
  return apiFetch<FluorographySchema>("/api/fluorography/");
}

// ─── Insurance ────────────────────────────────────────────────────────────

export function fetchInsurance(): Promise<InsuranceSchema> {
  return apiFetch<InsuranceSchema>("/api/insurance/");
}

// ─── History / Analytics ─────────────────────────────────────────────────

export function fetchVisits(): Promise<VisitsResponse> {
  return apiFetch<VisitsResponse>("/api/history/visits");
}

export function fetchUpcomingVisits(): Promise<UpcomingVisitsResponse> {
  return apiFetch<UpcomingVisitsResponse>("/api/schedule/upcoming");
}

// ─── Pipeline / Timeline / Trojan ─────────────────────────────────────────

export function fetchPipeline(): Promise<PipelineResponse> {
  return apiFetch<PipelineResponse>("/api/pipeline");
}

export function fetchTimeline(): Promise<TimelineResponse> {
  return apiFetch<TimelineResponse>("/api/timeline");
}

export function setInsuranceWarned(
  visitId: string,
  insurance_warned: boolean,
  bgs_application_number?: string,
): Promise<VisitItem> {
  return apiFetch<VisitItem>(`/api/schedule/${visitId}/insurance-warned`, {
    method: "PATCH",
    body: JSON.stringify({
      insurance_warned,
      ...(bgs_application_number
        ? { bgs_application_number }
        : {}),
    }),
  });
}

export function fetchTrojan(): Promise<TrojanResponse> {
  return apiFetch<TrojanResponse>("/api/trojan");
}

export function saveTrojan(data: {
  specialty: string;
  complaint_ids: string[];
  booster_ids: string[];
  notes?: string;
}): Promise<TrojanResponse> {
  return apiPut<TrojanResponse>("/api/trojan", data);
}

export function composeTrojan(data: {
  specialty: string;
  complaint_ids: string[];
  booster_ids: string[];
}): Promise<TrojanComposeResponse> {
  return apiPost<TrojanComposeResponse>("/api/trojan/compose", data);
}

/** Pipeline «Нужен промпт» → markdown + print HTML + Telegram document */
export function requestVisitPrompt(
  visitId: string,
  opts?: { dry_run?: boolean; chat_id?: number },
): Promise<{
  ok: boolean;
  visit_id: string;
  path: string;
  pdf_path?: string;
  pdf_ready?: boolean;
  download_url?: string;
  telegram_sent: boolean;
  telegram_error?: string | null;
  hint?: string;
  bytes?: number;
}> {
  return apiPost(`/api/visits/${encodeURIComponent(visitId)}/prompt`, {
    dry_run: opts?.dry_run ?? false,
    chat_id: opts?.chat_id,
  });
}

/** Download print-ready prompt package (HTML → Print / Save as PDF). */
export async function downloadVisitPrompt(visitId: string): Promise<void> {
  const blob = await apiFetchBlob(
    `/api/visits/${encodeURIComponent(visitId)}/prompt/download`,
  );
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `previsit-${visitId}-print.html`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function fetchCategories(): Promise<CategoriesResponse> {
  return apiFetch<CategoriesResponse>("/api/history/categories");
}

export function fetchAnalytics(category: string): Promise<AnalyticsResponse> {
  return apiFetch<AnalyticsResponse>(
    `/api/history/analytics?category=${encodeURIComponent(category)}`,
  );
}

export function fetchQuickRecords(): Promise<QuickRecord[]> {
  return apiFetch<QuickRecord[]>("/api/history/quick");
}

export function postQuickRecord(data: {
  bp?: string;
  weight_kg?: number;
  notes?: string;
}): Promise<QuickRecord> {
  return apiPost<QuickRecord>("/api/history/quick", data);
}

// ─── Admin ────────────────────────────────────────────────────────────────

export function fetchPendingUsers(): Promise<PendingList> {
  return apiFetch<PendingList>("/api/admin/pending");
}

export function approveUser(data: ApproveRequest): Promise<ApproveResponse> {
  return apiPost<ApproveResponse>("/api/admin/approve", data);
}
