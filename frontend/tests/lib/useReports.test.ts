import { afterEach, describe, expect, it, vi } from "vitest";
import { clearReportCache, setCachedReport } from "@/lib/reportCache";
import { getCachedReport } from "@/lib/reportCache";
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

describe("getReportWithCache", () => {
  afterEach(async () => {
    await clearReportCache();
    vi.restoreAllMocks();
  });

  it("returns API data and persists to cache", async () => {
    const { getReportWithCache } = await import("@/hooks/useReports");
    const mockFetch = vi.fn().mockResolvedValue(STUB);
    const result = await getReportWithCache(STUB.id, mockFetch);
    expect(result).toEqual(STUB);
    expect(await getCachedReport(STUB.id)).toEqual(STUB);
  });

  it("returns cached data when API fails", async () => {
    await setCachedReport(STUB);
    const { getReportWithCache } = await import("@/hooks/useReports");
    const mockFetch = vi.fn().mockRejectedValue(new Error("offline"));
    const result = await getReportWithCache(STUB.id, mockFetch);
    expect(result).toEqual(STUB);
  });

  it("throws when both API and cache miss", async () => {
    const { getReportWithCache } = await import("@/hooks/useReports");
    const mockFetch = vi.fn().mockRejectedValue(new Error("offline"));
    await expect(getReportWithCache("unknown", mockFetch)).rejects.toThrow(
      "offline",
    );
  });
});
