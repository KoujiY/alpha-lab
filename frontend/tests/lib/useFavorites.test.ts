import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useFavorites } from "@/hooks/useFavorites";

const KEY = "alpha-lab:favorites";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});

describe("useFavorites", () => {
  it("starts empty when localStorage is empty", () => {
    const { result } = renderHook(() => useFavorites());
    expect(result.current.favorites).toEqual([]);
    expect(result.current.isFavorite("2330")).toBe(false);
  });

  it("reads existing localStorage value on mount", () => {
    window.localStorage.setItem(KEY, JSON.stringify(["2330", "2317"]));
    const { result } = renderHook(() => useFavorites());
    expect(result.current.favorites).toEqual(["2330", "2317"]);
    expect(result.current.isFavorite("2330")).toBe(true);
  });

  it("toggle adds then removes a symbol", () => {
    const { result } = renderHook(() => useFavorites());
    act(() => result.current.toggle("2330"));
    expect(result.current.favorites).toEqual(["2330"]);
    act(() => result.current.toggle("2330"));
    expect(result.current.favorites).toEqual([]);
  });

  it("syncs to localStorage across toggle", () => {
    const { result } = renderHook(() => useFavorites());
    act(() => result.current.toggle("2330"));
    const raw = window.localStorage.getItem(KEY);
    expect(JSON.parse(raw ?? "[]")).toEqual(["2330"]);
  });

  it("responds to cross-tab storage event", () => {
    const { result } = renderHook(() => useFavorites());
    act(() => {
      window.localStorage.setItem(KEY, JSON.stringify(["2454"]));
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: KEY,
          newValue: JSON.stringify(["2454"]),
        }),
      );
    });
    expect(result.current.favorites).toEqual(["2454"]);
  });
});
