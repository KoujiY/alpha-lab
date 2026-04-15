import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TermTooltip } from "@/components/TermTooltip";

function renderWithQuery(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

afterEach(() => vi.restoreAllMocks());

describe("TermTooltip", () => {
  it("shows short definition on hover when term exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            PE: { term: "本益比", short: "股價相對 EPS 的倍數", detail: "", related: [] },
          }),
          { status: 200 }
        )
      )
    );

    renderWithQuery(<TermTooltip term="PE">本益比</TermTooltip>);
    const abbr = await screen.findByText("本益比");
    await userEvent.hover(abbr);
    expect(
      await screen.findByText(/股價相對 EPS 的倍數/)
    ).toBeInTheDocument();
  });

  it("falls back to abbr title when term missing from glossary", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))
    );

    renderWithQuery(<TermTooltip term="UNKNOWN">未知詞</TermTooltip>);
    const abbr = await screen.findByText("未知詞");
    expect(abbr).toHaveAttribute("title", "UNKNOWN");
  });
});
