import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "@/pages/SettingsPage";

const listSpy = vi.fn<() => Promise<string[]>>();
const clearSpy = vi.fn<() => Promise<void>>();

vi.mock("@/lib/reportCache", () => ({
  listCachedReportIds: () => listSpy(),
  clearReportCache: () => clearSpy(),
}));

vi.mock("@/api/stocks", () => ({
  listAllStocks: vi.fn(() =>
    Promise.resolve([
      { symbol: "2330", name: "台積電", industry: "半導體業", listed_date: null },
    ]),
  ),
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  listSpy.mockReset();
  clearSpy.mockReset();
});

afterEach(() => {
  window.localStorage.clear();
});

describe("SettingsPage", () => {
  it("shows cache count from listCachedReportIds and disables clear when empty", async () => {
    listSpy.mockResolvedValue([]);
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("cache-count")).toHaveTextContent("0"),
    );
    expect(screen.getByTestId("cache-clear")).toBeDisabled();
  });

  it("clicking clear opens confirm dialog, calls clearReportCache, and resets count", async () => {
    listSpy.mockResolvedValue(["a", "b", "c"]);
    clearSpy.mockResolvedValue();

    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("cache-count")).toHaveTextContent("3"),
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("cache-clear"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("cache-clear-confirm")).toBeInTheDocument(),
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("cache-clear-proceed"));
    });

    expect(clearSpy).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(screen.getByTestId("cache-count")).toHaveTextContent("0"),
    );
  });

  it("cancelling confirm dialog does not call clearReportCache", async () => {
    listSpy.mockResolvedValue(["a"]);
    clearSpy.mockResolvedValue();

    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("cache-count")).toHaveTextContent("1"),
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId("cache-clear"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("cache-clear-confirm")).toBeInTheDocument(),
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("cache-clear-cancel"));
    });

    expect(clearSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId("cache-count")).toHaveTextContent("1");
  });

  it("renders unknown-symbol fallback when stock is missing from listing", async () => {
    window.localStorage.setItem(
      "alpha-lab:favorites",
      JSON.stringify(["9999"]),
    );
    listSpy.mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("favorite-row-9999")).toBeInTheDocument();
    });
    await waitFor(() =>
      expect(screen.getByTestId("favorite-row-9999")).toHaveTextContent(
        "（查無資料，可能已下市）",
      ),
    );
  });
});
