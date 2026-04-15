import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreRadar } from "@/components/stock/ScoreRadar";
import type { FactorBreakdown } from "@/api/types";

const full: FactorBreakdown = {
  symbol: "2330",
  calc_date: "2026-04-15",
  value_score: 70,
  growth_score: 80,
  dividend_score: 50,
  quality_score: 90,
  total_score: 72.5,
};

const empty: FactorBreakdown = {
  symbol: "2330",
  calc_date: "2026-04-15",
  value_score: null,
  growth_score: null,
  dividend_score: null,
  quality_score: null,
  total_score: null,
};

describe("ScoreRadar", () => {
  it("renders title and formatted total score", () => {
    render(<ScoreRadar breakdown={full} />);
    expect(screen.getByText(/多因子評分/)).toBeInTheDocument();
    expect(screen.getByText("總分 72.5")).toBeInTheDocument();
  });

  it("shows dash when total is null", () => {
    render(<ScoreRadar breakdown={empty} />);
    expect(screen.getByText("總分 —")).toBeInTheDocument();
  });
});
