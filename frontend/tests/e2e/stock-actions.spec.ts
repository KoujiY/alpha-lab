import { test, expect, type Route } from "@playwright/test";

import glossary from "./fixtures/glossary.json" with { type: "json" };

const overview = {
  meta: {
    symbol: "2330",
    name: "台積電",
    industry: "半導體",
    listed_date: null,
  },
  prices: [],
  revenues: [],
  financials: [],
  institutional: [],
  margin: [],
  events: [],
};

const relatedReport = {
  id: "stock-2330-2026-04-14",
  type: "stock",
  title: "台積電深度",
  symbols: ["2330"],
  tags: ["半導體"],
  date: "2026-04-14",
  path: "analysis/stock-2330-2026-04-14.md",
  summary_line: "Q1 亮眼",
  starred: false,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/api/glossary", (route: Route) =>
    route.fulfill({ json: glossary }),
  );
  await page.route("**/api/stocks/2330/overview", (route: Route) =>
    route.fulfill({ json: overview }),
  );
  await page.route("**/api/stocks/2330/score", (route: Route) =>
    route.fulfill({ json: { symbol: "2330", latest: null } }),
  );
  await page.route("**/api/reports?*", (route: Route) =>
    route.fulfill({ json: [relatedReport] }),
  );
  await page.route("**/api/portfolios/saved", (route: Route) =>
    route.fulfill({ json: [] }),
  );
});

test("stock page shows actions and related reports", async ({ page }) => {
  await page.goto("/stocks/2330");
  await expect(page.getByTestId("stock-actions")).toBeVisible();
  await expect(page.getByTestId("related-reports")).toBeVisible();
  await expect(page.getByText("台積電深度")).toBeVisible();
});

test("favorite toggle persists across reload", async ({ page }) => {
  await page.goto("/stocks/2330");
  const fav = page.getByTestId("favorite-toggle");
  await expect(fav).toHaveText(/收藏/);
  await fav.click();
  await expect(fav).toHaveText(/已收藏/);
  await page.reload();
  await expect(page.getByTestId("favorite-toggle")).toHaveText(/已收藏/);
});

test("加入組合：今日報價不齊 → 彈 BaseDateConfirmDialog", async ({ page }) => {
  // 這個 test 的 saved portfolios list 要有一筆組合可以挑
  await page.route("**/api/portfolios/saved", (route: Route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        json: [
          {
            id: 42,
            style: "穩健",
            label: "主力組合",
            base_date: "2026-04-10",
            created_at: "2026-04-10T08:00:00Z",
          },
        ],
      });
    }
    return route.fallback();
  });
  await page.route("**/api/portfolios/saved/42", (route: Route) =>
    route.fulfill({
      json: {
        id: 42,
        style: "穩健",
        label: "主力組合",
        base_date: "2026-04-10",
        created_at: "2026-04-10T08:00:00Z",
        holdings: [
          { symbol: "2317", name: "鴻海", weight: 1.0, base_price: 100 },
        ],
      },
    }),
  );
  // probe 回「今日不齊」：2330 缺價、resolved_date = 2026-04-15
  await page.route("**/api/portfolios/saved/probe*", (route: Route) =>
    route.fulfill({
      json: {
        target_date: "2026-04-16",
        resolved_date: "2026-04-15",
        today_available: false,
        missing_today_symbols: ["2330"],
      },
    }),
  );

  await page.goto("/stocks/2330");
  await page.getByTestId("add-to-portfolio").click();
  await page.getByTestId("pick-portfolio-42").click();

  const dialog = page.getByTestId("save-confirm-dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("2330");
  await expect(dialog).toContainText("2026-04-15");
  await expect(page.getByTestId("save-confirm-cancel")).toBeVisible();
  await expect(page.getByTestId("save-confirm-proceed")).toBeEnabled();
});
