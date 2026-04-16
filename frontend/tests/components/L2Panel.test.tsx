import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { L2Panel } from "@/components/education/L2Panel";
import {
  L2PanelProvider,
  useL2Panel,
} from "@/components/education/L2PanelContext";

function Wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <L2PanelProvider>{children}</L2PanelProvider>
    </QueryClientProvider>
  );
}

function OpenButton({ topicId }: { topicId: string }) {
  const { openTopic } = useL2Panel();
  return (
    <button type="button" onClick={() => openTopic(topicId)}>
      open
    </button>
  );
}

afterEach(() => vi.restoreAllMocks());

describe("L2Panel", () => {
  it("is hidden by default", () => {
    render(
      <Wrapper>
        <L2Panel />
      </Wrapper>
    );
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("opens and renders markdown when topic requested", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "PE",
            title: "本益比深度",
            related_terms: ["EPS"],
            body_markdown: "# 本益比\n\n這是詳解段落。",
          }),
          { status: 200 }
        )
      )
    );

    render(
      <Wrapper>
        <OpenButton topicId="PE" />
        <L2Panel />
      </Wrapper>
    );
    await userEvent.click(screen.getByRole("button", { name: "open" }));
    expect(await screen.findByText("本益比深度")).toBeInTheDocument();
    expect(await screen.findByText(/這是詳解段落/)).toBeInTheDocument();
  });

  it("close button hides panel", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "PE",
            title: "T",
            related_terms: [],
            body_markdown: "body",
          }),
          { status: 200 }
        )
      )
    );

    render(
      <Wrapper>
        <OpenButton topicId="PE" />
        <L2Panel />
      </Wrapper>
    );
    await userEvent.click(screen.getByRole("button", { name: "open" }));
    await screen.findByText("T");
    await userEvent.click(screen.getByRole("button", { name: /關閉詳解面板/ }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });
});
