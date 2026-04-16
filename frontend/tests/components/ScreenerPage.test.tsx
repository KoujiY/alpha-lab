import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ScreenerPage } from "@/pages/ScreenerPage";

const mockFactors = {
  factors: [
    { key: "value_score", label: "價值 Value", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "growth_score", label: "成長 Growth", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "dividend_score", label: "股息 Dividend", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "quality_score", label: "品質 Quality", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "total_score", label: "總分 Total", min_value: 0, max_value: 100, default_min: 0, description: "" },
  ],
};

const mockFilterResult = {
  calc_date: "2026-04-17",
  total_count: 2,
  stocks: [
    { symbol: "2330", name: "台積電", industry: "半導體", value_score: 60, growth_score: 80, dividend_score: 50, quality_score: 90, total_score: 70 },
    { symbol: "2454", name: "聯發科", industry: "半導體", value_score: 40, growth_score: 95, dividend_score: 30, quality_score: 70, total_score: 58.75 },
  ],
};

vi.mock("@/api/screener", () => ({
  fetchFactors: vi.fn(() => Promise.resolve(mockFactors)),
  filterStocks: vi.fn(() => Promise.resolve(mockFilterResult)),
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ScreenerPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ScreenerPage", () => {
  it("renders factor sliders (excluding total_score)", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("價值 Value")).toBeInTheDocument();
    });
    expect(screen.queryByText("總分 Total")).not.toBeInTheDocument();
    expect(screen.getByTestId("slider-value_score")).toBeInTheDocument();
  });

  it("shows results after clicking filter button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("screener-filter-btn")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("screener-filter-btn"));
    await waitFor(() => {
      expect(screen.getByText("台積電")).toBeInTheDocument();
      expect(screen.getByText("聯發科")).toBeInTheDocument();
    });
  });

  it("displays heading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "選股篩選器" })).toBeInTheDocument();
    });
  });
});
