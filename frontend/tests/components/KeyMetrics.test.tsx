import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { KeyMetrics } from "@/components/stock/KeyMetrics";
import type { DailyPricePoint, FinancialPoint } from "@/api/types";

const price: DailyPricePoint = {
  trade_date: "2026-04-14",
  open: 600, high: 610, low: 595, close: 605, volume: 1,
};

const fin: FinancialPoint = {
  period: "2026Q1",
  revenue: null, gross_profit: null, operating_income: null,
  net_income: null, eps: 10,
  total_assets: null, total_liabilities: null, total_equity: null,
};

describe("KeyMetrics", () => {
  it("computes PE from close / eps", () => {
    render(<KeyMetrics latestPrice={price} latestFinancial={fin} />);
    expect(screen.getByText("60.5")).toBeInTheDocument();
  });

  it("renders em dashes when data missing", () => {
    render(<KeyMetrics latestPrice={undefined} latestFinancial={undefined} />);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });
});
