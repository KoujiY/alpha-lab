import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RevenueSection } from "@/components/stock/RevenueSection";

describe("RevenueSection", () => {
  it("shows empty placeholder when no data", () => {
    render(<RevenueSection points={[]} />);
    expect(screen.getByText(/尚無月營收資料/)).toBeInTheDocument();
  });

  it("renders section header with count hint", () => {
    render(
      <RevenueSection
        points={[
          { year: 2026, month: 3, revenue: 100_000_000, yoy_growth: 0.1, mom_growth: null },
        ]}
      />
    );
    expect(screen.getByText(/月營收（近 12 個月）/)).toBeInTheDocument();
  });
});
