import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import { TutorialModeProvider } from "@/contexts/TutorialModeProvider";
import { useTutorialMode } from "@/contexts/TutorialModeContext";

function wrapper({ children }: { children: ReactNode }) {
  return <TutorialModeProvider>{children}</TutorialModeProvider>;
}

describe("TutorialModeContext", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("defaults to full", () => {
    const { result } = renderHook(() => useTutorialMode(), { wrapper });
    expect(result.current.mode).toBe("full");
  });

  it("cycles full -> compact -> off -> full", () => {
    const { result } = renderHook(() => useTutorialMode(), { wrapper });
    act(() => result.current.cycle());
    expect(result.current.mode).toBe("compact");
    act(() => result.current.cycle());
    expect(result.current.mode).toBe("off");
    act(() => result.current.cycle());
    expect(result.current.mode).toBe("full");
  });

  it("persists to localStorage", () => {
    const { result } = renderHook(() => useTutorialMode(), { wrapper });
    act(() => result.current.setMode("off"));
    expect(window.localStorage.getItem("alpha-lab:tutorial-mode")).toBe("off");
  });

  it("setMode changes state immediately", () => {
    const { result } = renderHook(() => useTutorialMode(), { wrapper });
    act(() => result.current.setMode("compact"));
    expect(result.current.mode).toBe("compact");
  });

  it("throws when used outside provider", () => {
    expect(() => renderHook(() => useTutorialMode())).toThrow(
      /TutorialModeProvider/,
    );
  });
});
