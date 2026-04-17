import { afterEach, describe, expect, it } from "vitest";
import {
  clearReportCache,
  getCachedReport,
  listCachedReportIds,
  setCachedReport,
} from "@/lib/reportCache";
import type { ReportDetail } from "@/api/types";

const STUB: ReportDetail = {
  id: "stock-2330-2026-04-01",
  type: "stock",
  title: "台積電分析",
  symbols: ["2330"],
  tags: ["半導體"],
  date: "2026-04-01",
  path: "analysis/stock-2330-2026-04-01.md",
  summary_line: "Q1 展望正面",
  starred: false,
  body_markdown: "# 分析\n內容",
};

afterEach(async () => {
  await clearReportCache();
});

describe("reportCache", () => {
  it("returns undefined for unknown id", async () => {
    expect(await getCachedReport("nonexistent")).toBeUndefined();
  });

  it("round-trips a report", async () => {
    await setCachedReport(STUB);
    const result = await getCachedReport(STUB.id);
    expect(result).toEqual(STUB);
  });

  it("lists cached ids", async () => {
    await setCachedReport(STUB);
    const ids = await listCachedReportIds();
    expect(ids).toContain(STUB.id);
  });

  it("clears all cached reports", async () => {
    await setCachedReport(STUB);
    await clearReportCache();
    expect(await getCachedReport(STUB.id)).toBeUndefined();
    expect(await listCachedReportIds()).toHaveLength(0);
  });
});
