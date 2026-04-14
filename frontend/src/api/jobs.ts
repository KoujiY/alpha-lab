import { apiGet } from "./client";
import type { JobCreateRequest, JobResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function createCollectJob(
  req: JobCreateRequest,
): Promise<JobResponse> {
  const response = await fetch(`${API_BASE}/api/jobs/collect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    throw new Error(
      `createCollectJob failed: ${response.status} ${response.statusText}`,
    );
  }
  return (await response.json()) as JobResponse;
}

export async function getJobStatus(id: number): Promise<JobResponse> {
  return apiGet<JobResponse>(`/api/jobs/status/${id}`);
}
