import { test, expect, type Route } from "@playwright/test";

import stocksFixture from "./fixtures/stocks-list.json" with { type: "json" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/api/stocks?*", (route: Route) => {
    const url = new URL(route.request().url());
    const q = url.searchParams.get("q")?.toLowerCase() ?? "";
    const filtered = q
      ? stocksFixture.filter(
          (s) =>
            s.symbol.toLowerCase().includes(q) ||
            s.name.toLowerCase().includes(q),
        )
      : stocksFixture;
    route.fulfill({ json: filtered });
  });
  // Clear favorites before each run
  await page.addInitScript(() => {
    window.localStorage.removeItem("alpha-lab:favorites");
  });
});

test("stocks list renders rows and filters by search", async ({ page }) => {
  await page.goto("/stocks");
  await expect(page.getByRole("heading", { name: "股票瀏覽" })).toBeVisible();
  await expect(page.getByTestId("stock-row-2330")).toBeVisible();
  await expect(page.getByTestId("stock-row-2454")).toBeVisible();

  await page.getByTestId("stocks-search").fill("2330");
  await expect(page.getByTestId("stock-row-2330")).toBeVisible();
  await expect(page.getByTestId("stock-row-2454")).not.toBeVisible();
});

test("stocks list filters by industry", async ({ page }) => {
  await page.goto("/stocks");
  await page.getByTestId("stocks-industry").click();
  await page.getByRole("option", { name: "半導體業" }).click();
  await expect(page.getByTestId("stock-row-2330")).toBeVisible();
  await expect(page.getByTestId("stock-row-2454")).toBeVisible();
  await expect(page.getByTestId("stock-row-2412")).not.toBeVisible();
});

test("clicking stock name navigates to detail page", async ({ page }) => {
  await page.route("**/api/stocks/2330/overview", (route: Route) =>
    route.fulfill({
      json: {
        meta: stocksFixture[0],
        prices: [],
        revenues: [],
        financials: [],
        institutional: [],
        margin: [],
        events: [],
      },
    }),
  );
  await page.route("**/api/stocks/2330/score", (route: Route) =>
    route.fulfill({ json: { symbol: "2330", latest: null } }),
  );
  await page.route("**/api/glossary", (route: Route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/reports?*", (route: Route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/portfolios/saved", (route: Route) =>
    route.fulfill({ json: [] }),
  );

  await page.goto("/stocks");
  await page.getByTestId("stock-row-2330").getByRole("link").click();
  await expect(page).toHaveURL(/\/stocks\/2330$/);
});

test("favorite toggle persists across reload", async ({ page }) => {
  await page.goto("/stocks");
  await page.getByTestId("fav-toggle-2330").click();
  await expect(page.getByTestId("fav-toggle-2330")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.reload();
  await expect(page.getByTestId("fav-toggle-2330")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test("header 股票 link navigates to list", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "股票", exact: true }).click();
  await expect(page).toHaveURL(/\/stocks$/);
});
