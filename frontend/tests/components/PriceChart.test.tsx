import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PriceChart } from "@/components/stock/PriceChart";

// lightweight-charts uses canvas + ResizeObserver that jsdom doesn't provide;
// we only assert the wrapper renders the empty-data placeholder / mount div
// + aria section name. The canvas itself isn't asserted visually.
vi.mock("lightweight-charts", () => ({
  ColorType: { Solid: 0 },
  CandlestickSeries: Symbol("CandlestickSeries"),
  HistogramSeries: Symbol("HistogramSeries"),
  LineSeries: Symbol("LineSeries"),
  createChart: () => ({
    addSeries: () => ({
      setData: vi.fn(),
      priceScale: () => ({ applyOptions: vi.fn() }),
    }),
    timeScale: () => ({ fitContent: vi.fn() }),
    remove: vi.fn(),
  }),
}));

describe("PriceChart", () => {
  it("renders empty placeholder when no points", () => {
    render(<PriceChart points={[]} />);
    expect(screen.getByText("尚無股價資料")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "股價走勢" })).toBeInTheDocument();
  });

  it("renders chart container when points exist", () => {
    render(
      <PriceChart
        points={[
          {
            trade_date: "2026-04-15",
            open: 100,
            high: 105,
            low: 99,
            close: 104,
            volume: 1000,
          },
        ]}
      />,
    );
    expect(screen.getByTestId("price-chart")).toBeInTheDocument();
  });
});
