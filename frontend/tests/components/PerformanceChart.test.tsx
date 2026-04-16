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
      childBaseDate: "2026-04-17",
    });
    expect(result.forkDate).toBeNull();
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: null, self: 1.0 },
      { date: "2026-04-18", parent: null, self: 1.05 },
    ]);
  });

  it("scales self nav by parent_nav_at_fork and anchors fork at childBaseDate", () => {
    const result = buildChartSeries({
      points: [
        { date: "2026-04-18", nav: 1.0, daily_return: null },
        { date: "2026-04-21", nav: 1.08, daily_return: 0.08 },
      ],
      parentPoints: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
      ],
      parentNavAtFork: 1.1,
      childBaseDate: "2026-04-18",
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
      childBaseDate: "2026-04-18",
    });
    expect(result.forkDate).toBe("2026-04-18");
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: 1.0, self: null },
      { date: "2026-04-18", parent: 1.1, self: 1.1 },
    ]);
  });

  it("anchors fork at childBaseDate even when base_date is dropped by intersection", () => {
    // child.base_date = 4/17 但持股某支今天缺價，compute_performance 交集踢掉 4/17，
    // points[0] 從 4/18 開始；forkDate 應鎖在 base_date 而非 points[0].date
    const result = buildChartSeries({
      points: [
        { date: "2026-04-18", nav: 1.02, daily_return: null },
        { date: "2026-04-19", nav: 1.05, daily_return: 0.029 },
      ],
      parentPoints: [
        { date: "2026-04-15", nav: 1.0, daily_return: null },
        { date: "2026-04-16", nav: 1.07, daily_return: 0.07 },
      ],
      parentNavAtFork: 1.1,
      childBaseDate: "2026-04-17",
    });
    expect(result.forkDate).toBe("2026-04-17");
    expect(result.rows).toEqual([
      { date: "2026-04-15", parent: 1.0, self: null },
      { date: "2026-04-16", parent: 1.07, self: null },
      { date: "2026-04-17", parent: 1.1, self: 1.1 },
      { date: "2026-04-18", parent: null, self: 1.1 * 1.02 },
      { date: "2026-04-19", parent: null, self: 1.1 * 1.05 },
    ]);
  });

  it("skips duplicate self point when points[0].date equals childBaseDate", () => {
    const result = buildChartSeries({
      points: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
        { date: "2026-04-18", nav: 1.03, daily_return: 0.03 },
      ],
      parentPoints: [
        { date: "2026-04-16", nav: 1.0, daily_return: null },
      ],
      parentNavAtFork: 1.2,
      childBaseDate: "2026-04-17",
    });
    expect(result.forkDate).toBe("2026-04-17");
    expect(result.rows).toEqual([
      { date: "2026-04-16", parent: 1.0, self: null },
      { date: "2026-04-17", parent: 1.2, self: 1.2 },
      { date: "2026-04-18", parent: null, self: 1.2 * 1.03 },
    ]);
  });
});
