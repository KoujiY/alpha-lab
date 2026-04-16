import { describe, expect, it } from "vitest";

import { buildMergedHoldings } from "@/lib/portfolioMerge";

describe("buildMergedHoldings", () => {
  it("新 symbol：等比例稀釋既有持股後 append", () => {
    const result = buildMergedHoldings({
      existing: [
        { symbol: "2330", name: "台積電", weight: 0.9, base_price: 2080 },
        { symbol: "2317", name: "鴻海", weight: 0.1, base_price: 100 },
      ],
      symbol: "2454",
      name: "聯發科",
      delta: 0.1,
    });
    expect(result).toHaveLength(3);
    expect(result[0].weight).toBeCloseTo(0.81);
    expect(result[1].weight).toBeCloseTo(0.09);
    expect(result[2]).toEqual({
      symbol: "2454",
      name: "聯發科",
      weight: 0.1,
      base_price: 0,
    });
    expect(result.reduce((s, h) => s + h.weight, 0)).toBeCloseTo(1.0);
    // 所有 base_price 都設 0 讓後端 rebase
    result.forEach((h) => expect(h.base_price).toBe(0));
  });

  it("既有 symbol：稀釋後 += delta，不會出現兩筆同 symbol", () => {
    const result = buildMergedHoldings({
      existing: [
        { symbol: "2330", name: "台積電", weight: 0.9, base_price: 2080 },
        { symbol: "2317", name: "鴻海", weight: 0.1, base_price: 100 },
      ],
      symbol: "2330",
      name: "台積電",
      delta: 0.1,
    });
    expect(result).toHaveLength(2);
    const tsmc = result.find((h) => h.symbol === "2330");
    const hon = result.find((h) => h.symbol === "2317");
    expect(tsmc?.weight).toBeCloseTo(0.91);
    expect(hon?.weight).toBeCloseTo(0.09);
    expect(result.reduce((s, h) => s + h.weight, 0)).toBeCloseTo(1.0);
  });

  it("權重 ≤ 0 或 ≥ 1：拒絕", () => {
    const existing = [
      { symbol: "2330", name: "台積電", weight: 1.0, base_price: 2080 },
    ];
    expect(() =>
      buildMergedHoldings({
        existing,
        symbol: "2317",
        name: "鴻海",
        delta: 0,
      }),
    ).toThrow("權重需介於 1% 到 99%");
    expect(() =>
      buildMergedHoldings({
        existing,
        symbol: "2317",
        name: "鴻海",
        delta: 1,
      }),
    ).toThrow("權重需介於 1% 到 99%");
    expect(() =>
      buildMergedHoldings({
        existing,
        symbol: "2317",
        name: "鴻海",
        delta: Number.NaN,
      }),
    ).toThrow("權重需介於 1% 到 99%");
  });

  it("全倉單一 symbol 又加碼同 symbol：拒絕（稀釋後仍為自己，無效操作）", () => {
    expect(() =>
      buildMergedHoldings({
        existing: [
          { symbol: "2330", name: "台積電", weight: 1.0, base_price: 2080 },
        ],
        symbol: "2330",
        name: "台積電",
        delta: 0.1,
      }),
    ).toThrow("全倉");
  });

  it("全倉單一 symbol 加碼不同 symbol：正常稀釋 + append", () => {
    const result = buildMergedHoldings({
      existing: [
        { symbol: "2330", name: "台積電", weight: 1.0, base_price: 2080 },
      ],
      symbol: "2317",
      name: "鴻海",
      delta: 0.2,
    });
    expect(result).toHaveLength(2);
    expect(result[0].weight).toBeCloseTo(0.8);
    expect(result[1].weight).toBeCloseTo(0.2);
  });
});
