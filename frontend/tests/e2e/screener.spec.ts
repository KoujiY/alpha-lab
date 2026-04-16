import { test, expect, type Route } from "@playwright/test";

import factors from "./fixtures/screener-factors.json" with { type: "json" };
import filterResult from "./fixtures/screener-filter.json" with { type: "json" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/screener/factors", (route: Route) =>
    route.fulfill({ json: factors })
  );
  await page.route("**/api/screener/filter", (route: Route) =>
    route.fulfill({ json: filterResult })
  );
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } })
  );
});

test("screener page shows factor sliders", async ({ page }) => {
  await page.goto("/screener");
  await expect(page.getByRole("heading", { name: "選股篩選器" })).toBeVisible();
  await expect(page.getByText("價值 Value")).toBeVisible();
  await expect(page.getByText("成長 Growth")).toBeVisible();
  await expect(page.getByText("品質 Quality")).toBeVisible();
});

test("screener filter button triggers search and shows results", async ({ page }) => {
  await page.goto("/screener");
  await page.getByTestId("screener-filter-btn").click();
  await expect(page.getByText("台積電")).toBeVisible();
  await expect(page.getByText("鴻海")).toBeVisible();
  await expect(page.getByText("聯發科")).toBeVisible();
  await expect(page.getByText("共 3 檔符合")).toBeVisible();
});

test("screener result stock links to stock page", async ({ page }) => {
  await page.goto("/screener");
  await page.getByTestId("screener-filter-btn").click();
  await expect(page.getByText("台積電")).toBeVisible();
  const link = page.getByRole("link", { name: "2330" });
  await expect(link).toHaveAttribute("href", "/stocks/2330");
});

test("screener nav link exists in header", async ({ page }) => {
  await page.goto("/screener");
  await expect(page.getByRole("link", { name: "選股篩選" })).toBeVisible();
});

test("screener shows 409 guidance when no scores", async ({ page }) => {
  await page.route("**/api/screener/filter", (route: Route) =>
    route.fulfill({ status: 409, json: { detail: "no scores available" } })
  );
  await page.goto("/screener");
  await page.getByTestId("screener-filter-btn").click();
  await expect(page.getByText("尚無評分資料")).toBeVisible();
});
