import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { HoldingsTable } from "@/components/portfolio/HoldingsTable";
import type { Holding } from "@/api/types";

const sampleHoldings: Holding[] = [
  {
    symbol: "2330",
    name: "台積電",
    weight: 0.3,
    score_breakdown: {
      symbol: "2330",
      calc_date: "2026-04-17",
      value_score: 60,
      growth_score: 70,
      dividend_score: 80,
      quality_score: 90,
      total_score: 80,
    },
    reasons: [
      "平衡組配置偏好：Value / Growth / Dividend / Quality 四面並重。",
      "Quality 90 分：ROE、毛利率、負債結構等體質穩健。",
    ],
  },
];

describe("HoldingsTable", () => {
  it("renders holding basic fields", () => {
    render(<HoldingsTable holdings={sampleHoldings} />);
    expect(screen.getByText("2330")).toBeInTheDocument();
    expect(screen.getByText("台積電")).toBeInTheDocument();
    expect(screen.getByText("30.0%")).toBeInTheDocument();
  });

  it("reasons are collapsed by default and expandable", async () => {
    render(<HoldingsTable holdings={sampleHoldings} />);
    expect(screen.queryByText(/四面並重/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "查看理由" }));
    expect(screen.getByText(/四面並重/)).toBeInTheDocument();
    expect(screen.getByText(/Quality 90 分/)).toBeInTheDocument();
  });

  it("shows dash when reasons empty", () => {
    render(
      <HoldingsTable
        holdings={[{ ...sampleHoldings[0], reasons: [] }]}
      />
    );
    expect(screen.queryByRole("button", { name: "查看理由" })).not.toBeInTheDocument();
  });

  it("shows empty state when no holdings", () => {
    render(<HoldingsTable holdings={[]} />);
    expect(screen.getByText("此組合無持股候選。")).toBeInTheDocument();
  });
});
