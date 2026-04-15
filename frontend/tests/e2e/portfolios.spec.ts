import { test, expect, type Route } from "@playwright/test";

import fixture from "./fixtures/portfolios-recommend.json" with { type: "json" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/portfolios/recommend**", (route: Route) =>
    route.fulfill({ json: fixture })
  );
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } })
  );
});

test("portfolios page shows three tabs and top pick badge on balanced", async ({ page }) => {
  await page.goto("/portfolios");
  await expect(page.getByRole("heading", { name: "投資組合推薦" })).toBeVisible();
  await expect(page.getByRole("button", { name: /保守組/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /平衡組.*最推薦/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /積極組/ })).toBeVisible();
});

test("portfolios page switches tab and shows different holdings", async ({ page }) => {
  await page.goto("/portfolios");
  await expect(page.getByText("聯發科")).toBeVisible();

  await page.getByRole("button", { name: /積極組/ }).click();
  await expect(page.getByText("長榮")).toBeVisible();

  await page.getByRole("button", { name: /保守組/ }).click();
  await expect(page.getByText("台積電")).toBeVisible();
});
