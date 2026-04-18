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
  await expect(fav).toHaveAttribute("aria-pressed", "false");
  await fav.click();
  await expect(fav).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(page.getByTestId("favorite-toggle")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
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
        symbol_statuses: { "2330": "today_missing" },
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

test("加入組合時 POST payload 帶 parent_id 血緣", async ({ page }) => {
  const parentMeta = {
    id: 42,
    style: "balanced",
    label: "主力組合",
    note: null,
    base_date: "2026-04-17",
    created_at: "2026-04-17T00:00:00Z",
    holdings_count: 1,
    parent_id: null,
    parent_nav_at_fork: null,
  };
  const capturedBodies: Array<Record<string, unknown>> = [];

  await page.route("**/api/portfolios/saved", (route: Route) => {
    const req = route.request();
    if (req.method() === "GET") {
      return route.fulfill({ json: [parentMeta] });
    }
    if (req.method() === "POST") {
      capturedBodies.push(req.postDataJSON() as Record<string, unknown>);
      return route.fulfill({
        json: {
          ...parentMeta,
          id: 99,
          label: "主力組合 + 2330",
          parent_id: 42,
          parent_nav_at_fork: 1.0,
        },
      });
    }
    return route.fallback();
  });
  await page.route("**/api/portfolios/saved/42", (route: Route) =>
    route.fulfill({
      json: {
        ...parentMeta,
        holdings: [
          { symbol: "2317", name: "鴻海", weight: 1.0, base_price: 100 },
        ],
      },
    }),
  );
  await page.route("**/api/portfolios/saved/probe*", (route: Route) =>
    route.fulfill({
      json: {
        target_date: "2026-04-17",
        resolved_date: "2026-04-17",
        today_available: true,
        missing_today_symbols: [],
        symbol_statuses: {},
      },
    }),
  );

  await page.goto("/stocks/2330");
  await page.getByTestId("add-to-portfolio").click();
  await page.getByTestId("pick-portfolio-42").click();

  await expect.poll(() => capturedBodies.length).toBeGreaterThan(0);
  expect(capturedBodies[0]?.parent_id).toBe(42);
  expect(capturedBodies[0]?.label).toBe("主力組合 + 2330");
});
