import { describe, expect, it } from "vitest";

import { buildChartSeries } from "@/components/portfolio/PerformanceChart";

describe("buildChartSeries", () => {
  it("returns self-only series when parent info absent", () => {
    const result = buildChartSeries({
      points: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
        { date: "2026-04-18", nav: 1.05, daily_return: 0.05 },
      ],
      parentPoints: null,
      parentNavAtFork: null,
    });
    expect(result.forkDate).toBeNull();
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: null, self: 1.0 },
      { date: "2026-04-18", parent: null, self: 1.05 },
    ]);
  });

  it("scales self nav by parent_nav_at_fork and prepends parent points", () => {
    const result = buildChartSeries({
      points: [
        { date: "2026-04-18", nav: 1.0, daily_return: null },
        { date: "2026-04-21", nav: 1.08, daily_return: 0.08 },
      ],
      parentPoints: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
      ],
      parentNavAtFork: 1.1,
    });
    expect(result.forkDate).toBe("2026-04-18");
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: 1.0, self: null },
      { date: "2026-04-18", parent: 1.1, self: 1.1 },
      { date: "2026-04-21", parent: null, self: 1.1 * 1.08 },
    ]);
  });

  it("handles empty self points by returning only parent series", () => {
    const result = buildChartSeries({
      points: [],
      parentPoints: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
      ],
      parentNavAtFork: 1.1,
    });
    expect(result.forkDate).toBeNull();
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: 1.0, self: null },
    ]);
  });
});
