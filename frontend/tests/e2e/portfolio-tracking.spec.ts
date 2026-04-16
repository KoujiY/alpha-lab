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
