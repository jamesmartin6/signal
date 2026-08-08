export type LeadStatus =
  | "pending"
  | "extracting"
  | "classifying"
  | "enriching"
  | "routing"
  | "done"
  | "failed";

export type PipelineStage = "extract" | "classify" | "enrich" | "route";

export interface RawInput {
  name: string;
  company: string;
  bio_or_linkedin_url: string;
}

export interface StageResult {
  id: string;
  stage: PipelineStage;
  prompt_version: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  model: string;
  latency_ms: number;
  success: boolean;
  created_at: string;
}

export interface Lead {
  id: string;
  raw_input: RawInput;
  status: LeadStatus;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadDetail extends Lead {
  stage_results: StageResult[];
}

export interface PaginatedLeads {
  total: number;
  limit: number;
  offset: number;
  items: Lead[];
}

export interface SkippedRow {
  row_number: number;
  reason: string;
}

export interface UploadResponse {
  created: number;
  skipped: number;
  skipped_rows: SkippedRow[];
  lead_ids: string[];
}

export interface EvalRun {
  id: string;
  prompt_version: string;
  stage: PipelineStage;
  total_cases: number;
  passed_cases: number;
  pass_rate: number;
  created_at: string;
}
