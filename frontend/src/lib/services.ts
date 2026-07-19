/**
 * Typed API service functions for Sasha Health.
 *
 * Each function wraps apiFetch with correct return types matching
 * the backend Pydantic schemas.
 */

import { apiDelete, apiFetch, apiPost, apiPut } from "./api";
import type {
  AnalyticsResponse,
  ApproveRequest,
  ApproveResponse,
  CategoriesResponse,
  FluorographySchema,
  InsuranceSchema,
  Medication,
  PendingList,
  ProfileSchema,
  QuickRecord,
  StrategySchema,
  UpcomingVisitsResponse,
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
