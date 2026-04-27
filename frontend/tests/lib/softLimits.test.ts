import { describe, expect, it } from "vitest";

import type { SavedHolding } from "@/api/types";
import { SOFT_LIMITS, checkSoftLimits } from "@/lib/softLimits";

function h(symbol: string, weight: number): SavedHolding {
  return { symbol, name: symbol, weight, base_price: 0 };
}

describe("checkSoftLimits", () => {
  it("returns empty for a clean 10-stock 10% each portfolio", () => {
    const holdings = Array.from({ length: 10 }, (_, i) => h(`S${i}`, 0.1));
    expect(checkSoftLimits(holdings)).toEqual([]);
  });

  it("warns when holdings exceed 20", () => {
    const holdings = Array.from({ length: 21 }, (_, i) =>
      h(`S${i}`, 1 / 21),
    );
    const result = checkSoftLimits(holdings);
    expect(result.length).toBe(1);
    expect(result[0].code).toBe("too_many_holdings");
  });

  it("warns when a single stock weight exceeds 40%", () => {
    const holdings = [h("A", 0.5), h("B", 0.3), h("C", 0.2)];
    const result = checkSoftLimits(holdings);
    expect(result[0].code).toBe("single_weight_too_high");
    expect(result[0].symbols).toEqual(["A"]);
  });

  it("warns when any stock weight is below 0.5%", () => {
    const holdings = [h("A", 0.996), h("B", 0.004)];
    const result = checkSoftLimits(holdings);
    expect(result.some((w) => w.code === "weight_too_small")).toBe(true);
    expect(
      result.find((w) => w.code === "weight_too_small")?.symbols,
    ).toEqual(["B"]);
  });

  it("can emit multiple warnings at once", () => {
    const holdings = [
      h("A", 0.8),
      h("B", 0.003),
      ...Array.from({ length: 20 }, (_, i) => h(`C${i}`, 0.197 / 20)),
    ];
    const codes = checkSoftLimits(holdings).map((w) => w.code);
    expect(codes).toContain("too_many_holdings");
    expect(codes).toContain("single_weight_too_high");
    expect(codes).toContain("weight_too_small");
  });

  it("exposes thresholds via SOFT_LIMITS constant", () => {
    expect(SOFT_LIMITS.MAX_HOLDINGS).toBe(20);
    expect(SOFT_LIMITS.MAX_SINGLE_WEIGHT).toBe(0.4);
    expect(SOFT_LIMITS.MIN_SINGLE_WEIGHT).toBe(0.005);
  });
});
