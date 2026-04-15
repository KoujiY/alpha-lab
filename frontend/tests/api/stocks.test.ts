import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchStockOverview, searchStocks } from "@/api/stocks";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("stocks api", () => {
  it("fetchStockOverview calls correct path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          meta: { symbol: "2330", name: "台積電", industry: null, listed_date: null },
          prices: [], revenues: [], financials: [],
          institutional: [], margin: [], events: [],
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchStockOverview("2330");
    expect(result.meta.symbol).toBe("2330");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/stocks/2330/overview")
    );
  });

  it("searchStocks builds query string", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 })
    );
    vi.stubGlobal("fetch", fetchMock);

    await searchStocks("台積");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/stocks\?q=.*&limit=20/)
    );
  });
});
