export type JobType = "twse_prices" | "mops_revenue";

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface JobResponse {
  id: number;
  job_type: string;
  status: JobStatus;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface JobCreateRequest {
  type: JobType;
  params: Record<string, unknown>;
}
