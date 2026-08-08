import type { EvalRun, LeadDetail, PaginatedLeads, UploadResponse } from "../types/lead";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, init);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = (await resp.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export function uploadLeadsCsv(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadResponse>("/leads/upload", { method: "POST", body: formData });
}

export function fetchLeads(limit = 200, offset = 0): Promise<PaginatedLeads> {
  return request<PaginatedLeads>(`/leads?limit=${limit}&offset=${offset}`);
}

export function fetchLeadDetail(id: string): Promise<LeadDetail> {
  return request<LeadDetail>(`/leads/${id}`);
}

export function fetchEvalRuns(): Promise<EvalRun[]> {
  return request<EvalRun[]>("/evals");
}
