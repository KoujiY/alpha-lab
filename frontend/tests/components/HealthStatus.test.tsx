import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { ReactElement } from "react";
import { HealthStatus } from "@/components/HealthStatus";

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("HealthStatus", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows success when backend responds ok", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "ok",
          version: "0.1.0",
          timestamp: new Date().toISOString(),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderWithClient(<HealthStatus />);
    expect(await screen.findByText(/後端連線正常/)).toBeInTheDocument();
  });

  it("shows error when backend fails", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("network error"),
    );

    renderWithClient(<HealthStatus />);
    expect(await screen.findByText(/後端連線失敗/)).toBeInTheDocument();
  });
});
