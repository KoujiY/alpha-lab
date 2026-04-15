import { test, expect, type Route } from "@playwright/test";

import overview from "./fixtures/stock-2330.json" with { type: "json" };
import glossary from "./fixtures/glossary.json" with { type: "json" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/stocks/2330/overview", (route: Route) =>
    route.fulfill({ json: overview })
  );
  await page.route("**/api/glossary", (route: Route) =>
    route.fulfill({ json: glossary })
  );
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } })
  );
});

test("stock page renders all sections", async ({ page }) => {
  await page.goto("/stocks/2330");
  await expect(page.getByRole("heading", { name: /2330 台積電/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "月營收" })).toBeVisible();
  await expect(page.getByRole("region", { name: "季報摘要" })).toBeVisible();
  await expect(page.getByRole("region", { name: "三大法人" })).toBeVisible();
  await expect(page.getByRole("region", { name: "融資融券" })).toBeVisible();
  await expect(page.getByRole("region", { name: "重大訊息" })).toBeVisible();
});

test("term tooltip shows short definition on hover", async ({ page }) => {
  await page.goto("/stocks/2330");
  const peLabel = page.getByText("本益比 (PE)", { exact: true });
  await peLabel.hover();
  await expect(page.getByRole("tooltip")).toContainText("股價相對每股盈餘的倍數");
});

test("header search navigates to stock page", async ({ page }) => {
  await page.goto("/");
  const input = page.getByLabel("股票代號");
  await input.fill("2330");
  await input.press("Enter");
  await expect(page).toHaveURL(/\/stocks\/2330/);
});
