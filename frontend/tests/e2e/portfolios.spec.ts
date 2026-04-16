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

test("portfolios page shows recommendation reasons on click", async ({ page }) => {
  await page.goto("/portfolios");
  await page.getByRole("button", { name: /查看理由/ }).first().click();
  await expect(page.getByText(/平衡組配置偏好/)).toBeVisible();
});

test("portfolios page save-report button triggers save with flag", async ({ page }) => {
  const saveRequests: string[] = [];
  await page.route("**/api/portfolios/recommend**", async (route: Route) => {
    saveRequests.push(route.request().url());
    await route.fulfill({ json: fixture });
  });

  await page.goto("/portfolios");
  await expect(page.getByTestId("save-portfolio-report")).toBeVisible();
  await page.getByTestId("save-portfolio-report").click();
  await expect(page.getByText(/已儲存 portfolio-/)).toBeVisible();

  expect(saveRequests.some((url) => url.includes("save_report=true"))).toBe(true);
});
