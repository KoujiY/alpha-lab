import { describe, expect, it } from "vitest";

import type { SavedHolding } from "@/api/types";
import {
  isWeightSumValid,
  normalizeToOne,
  rebalanceAfterEdit,
} from "@/lib/weightAdjust";

function h(symbol: string, weight: number): SavedHolding {
  return { symbol, name: symbol, weight, base_price: 0 };
}

describe("rebalanceAfterEdit", () => {
  it("scales other holdings proportionally so total sums to 1", () => {
    const input = [h("A", 0.5), h("B", 0.3), h("C", 0.2)];
    const result = rebalanceAfterEdit(input, "A", 0.6);
    expect(result.find((x) => x.symbol === "A")?.weight).toBe(0.6);
    expect(
      result.reduce((s, x) => s + x.weight, 0),
    ).toBeCloseTo(1, 10);
    expect(result.find((x) => x.symbol === "B")?.weight).toBeCloseTo(
      (0.3 / 0.5) * 0.4,
      10,
    );
    expect(result.find((x) => x.symbol === "C")?.weight).toBeCloseTo(
      (0.2 / 0.5) * 0.4,
      10,
    );
  });

  it("clamps editedWeight below 0 to 0", () => {
    const input = [h("A", 0.5), h("B", 0.5)];
    const result = rebalanceAfterEdit(input, "A", -0.1);
    expect(result.find((x) => x.symbol === "A")?.weight).toBe(0);
    expect(result.find((x) => x.symbol === "B")?.weight).toBeCloseTo(1, 10);
  });

  it("clamps editedWeight above 1 to 1, zeros out others", () => {
    const input = [h("A", 0.5), h("B", 0.5)];
    const result = rebalanceAfterEdit(input, "A", 1.5);
    expect(result.find((x) => x.symbol === "A")?.weight).toBe(1);
    expect(result.find((x) => x.symbol === "B")?.weight).toBeCloseTo(0, 10);
  });

  it("single-holding always returns weight 1", () => {
    const input = [h("A", 0.5)];
    const result = rebalanceAfterEdit(input, "A", 0.3);
    expect(result).toEqual([{ ...input[0], weight: 1 }]);
  });

  it("returns input unchanged if editedSymbol not found", () => {
    const input = [h("A", 0.6), h("B", 0.4)];
    const result = rebalanceAfterEdit(input, "ZZZ", 0.5);
    expect(result).toEqual(input);
  });

  it("distributes remainder evenly when all other weights are 0", () => {
    const input = [h("A", 1), h("B", 0), h("C", 0)];
    const result = rebalanceAfterEdit(input, "A", 0.5);
    expect(result.find((x) => x.symbol === "A")?.weight).toBe(0.5);
    expect(result.find((x) => x.symbol === "B")?.weight).toBeCloseTo(0.25);
    expect(result.find((x) => x.symbol === "C")?.weight).toBeCloseTo(0.25);
  });
});

describe("isWeightSumValid", () => {
  it("returns true when sum is within 1e-6 of 1", () => {
    expect(isWeightSumValid([h("A", 0.5), h("B", 0.5)])).toBe(true);
    expect(
      isWeightSumValid([h("A", 0.333333), h("B", 0.333333), h("C", 0.333334)]),
    ).toBe(true);
  });
  it("returns false when off", () => {
    expect(isWeightSumValid([h("A", 0.4), h("B", 0.4)])).toBe(false);
  });
});

describe("normalizeToOne", () => {
  it("scales holdings to sum exactly 1", () => {
    const result = normalizeToOne([h("A", 0.4), h("B", 0.4)]);
    expect(isWeightSumValid(result)).toBe(true);
    expect(result[0].weight).toBeCloseTo(0.5, 10);
    expect(result[1].weight).toBeCloseTo(0.5, 10);
  });

  it("preserves relative ratios", () => {
    const result = normalizeToOne([h("A", 0.2), h("B", 0.6)]);
    expect(result[0].weight / result[1].weight).toBeCloseTo(0.2 / 0.6, 10);
    expect(isWeightSumValid(result)).toBe(true);
  });

  it("leaves an all-zero list untouched (caller handles)", () => {
    const zero = [h("A", 0), h("B", 0)];
    expect(normalizeToOne(zero)).toEqual(zero);
  });
});
