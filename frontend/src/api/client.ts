const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {
    // body not JSON or empty — fall through
  }
  return `${response.status} ${response.statusText}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API error: ${await readErrorDetail(response)}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(
  path: string,
  params?: Record<string, string>,
  body?: unknown,
): Promise<T> {
  const query = params ? `?${new URLSearchParams(params).toString()}` : "";
  const response = await fetch(`${API_BASE}${path}${query}`, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`API error: ${await readErrorDetail(response)}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error: ${await readErrorDetail(response)}`);
  }
  return response.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`API error: ${await readErrorDetail(response)}`);
  }
}
