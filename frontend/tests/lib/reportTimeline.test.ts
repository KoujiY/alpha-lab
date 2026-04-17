import { describe, expect, it } from "vitest";

import type { ReportMeta } from "@/api/types";
import { groupReportsByMonth } from "@/lib/reportTimeline";

function meta(id: string, date: string): ReportMeta {
  return {
    id,
    type: "stock",
    title: id,
    symbols: [],
    tags: [],
    date,
    path: `analysis/${id}.md`,
    summary_line: "",
    starred: false,
  };
}

describe("groupReportsByMonth", () => {
  it("groups reports by YYYY-MM, months sorted desc", () => {
    const result = groupReportsByMonth([
      meta("a", "2026-04-15"),
      meta("b", "2026-04-01"),
      meta("c", "2026-03-20"),
    ]);
    expect(result.map((g) => g.month)).toEqual(["2026-04", "2026-03"]);
    expect(result[0].items.map((r) => r.id)).toEqual(["a", "b"]);
    expect(result[1].items.map((r) => r.id)).toEqual(["c"]);
  });

  it("preserves within-month input order", () => {
    const result = groupReportsByMonth([
      meta("old", "2026-04-01"),
      meta("new", "2026-04-20"),
    ]);
    expect(result[0].items.map((r) => r.id)).toEqual(["old", "new"]);
  });

  it("returns empty array for empty input", () => {
    expect(groupReportsByMonth([])).toEqual([]);
  });

  it("handles single month", () => {
    const result = groupReportsByMonth([meta("a", "2026-04-15")]);
    expect(result).toHaveLength(1);
    expect(result[0].month).toBe("2026-04");
  });
});
