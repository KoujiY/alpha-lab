import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { RevenueSection } from "@/components/stock/RevenueSection";

function renderWithQuery(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("RevenueSection", () => {
  it("shows empty placeholder when no data", () => {
    renderWithQuery(<RevenueSection points={[]} />);
    expect(screen.getByText(/尚無月營收資料/)).toBeInTheDocument();
  });

  it("renders section header with count hint", () => {
    renderWithQuery(
      <RevenueSection
        points={[
          { year: 2026, month: 3, revenue: 100_000_000, yoy_growth: 0.1, mom_growth: null },
        ]}
      />
    );
    const heading = screen.getByRole("heading", { level: 2 });
    expect(heading.textContent).toContain("月營收");
    expect(heading.textContent).toContain("近 12 個月");
  });
});
