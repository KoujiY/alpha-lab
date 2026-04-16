import { test, expect, type Route } from "@playwright/test";

import savedList from "./fixtures/saved-portfolios.json" with { type: "json" };
import performance from "./fixtures/performance.json" with { type: "json" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } })
  );
  await page.route("**/api/portfolios/saved", (route: Route) =>
    route.fulfill({ json: savedList })
  );
  await page.route("**/api/portfolios/saved/1/performance", (route: Route) =>
    route.fulfill({ json: performance })
  );
});

test("tracking page renders saved portfolio with performance", async ({
  page,
}) => {
  await page.goto("/portfolios/1");
  await expect(page.getByTestId("portfolio-tracking-page")).toBeVisible();
  await expect(page.getByText("平衡組 2026-04-17")).toBeVisible();
  await expect(page.getByText("累積報酬")).toBeVisible();
  await expect(page.getByText("5.00%")).toBeVisible();
});

test("forked 組合追蹤頁顯示血緣資訊與連續報酬卡片", async ({ page }) => {
  await page.route("**/api/portfolios/saved/2/performance", (route: Route) =>
    route.fulfill({
      json: {
        portfolio: {
          id: 2,
          style: "balanced",
          label: "child-test",
          note: null,
          base_date: "2026-04-17",
          created_at: "2026-04-17T00:00:00Z",
          holdings_count: 1,
          parent_id: 1,
          parent_nav_at_fork: 1.1,
          holdings: [
            { symbol: "2330", name: "台積電", weight: 1.0, base_price: 660 },
          ],
        },
        points: [
          { date: "2026-04-17", nav: 1.0, daily_return: null },
          { date: "2026-04-18", nav: 1.05, daily_return: 0.05 },
        ],
        latest_nav: 1.05,
        total_return: 0.05,
        parent_points: [
          { date: "2026-04-14", nav: 1.0, daily_return: null },
          { date: "2026-04-15", nav: 1.05, daily_return: 0.05 },
        ],
        parent_nav_at_fork: 1.1,
      },
    }),
  );

  await page.goto("/portfolios/2");
  await expect(page.getByTestId("lineage-info")).toBeVisible();
  await expect(page.getByTestId("lineage-parent-link")).toHaveAttribute(
    "href",
    "/portfolios/1",
  );
  await expect(page.getByTestId("continuous-return-card")).toBeVisible();
});
