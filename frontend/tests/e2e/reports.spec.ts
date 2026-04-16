import { test, expect, type Route } from "@playwright/test";

import listFixture from "./fixtures/reports-list.json" with { type: "json" };
import detailFixture from "./fixtures/reports-portfolio-detail.json" with {
  type: "json",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/api/reports/portfolio-2026-04-15", (route: Route) =>
    route.fulfill({ json: detailFixture }),
  );
  await page.route("**/api/reports**", (route: Route) => {
    const url = route.request().url();
    if (url.includes("type=stock")) {
      route.fulfill({
        json: listFixture.filter((r) => r.type === "stock"),
      });
      return;
    }
    route.fulfill({ json: listFixture });
  });
});

test("reports list shows cards and filters by type", async ({ page }) => {
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "分析回顧" })).toBeVisible();
  await expect(page.getByText("本次推薦組合 2026-04-15")).toBeVisible();
  await expect(page.getByText("台積電深度分析")).toBeVisible();

  await page.getByRole("button", { name: "個股" }).click();
  await expect(page.getByText("台積電深度分析")).toBeVisible();
  await expect(page.getByText("本次推薦組合 2026-04-15")).not.toBeVisible();
});

test("report card link navigates to detail and renders markdown", async ({ page }) => {
  await page.goto("/reports");
  await page.getByRole("link", { name: /本次推薦組合/ }).click();
  await expect(page).toHaveURL(/\/reports\/portfolio-2026-04-15$/);
  await expect(
    page.getByRole("heading", { name: "本次推薦組合 2026-04-15", level: 1 }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "平衡型", level: 2 }),
  ).toBeVisible();
  await expect(page.getByText("價值面亮眼")).toBeVisible();

  await page.getByRole("link", { name: "← 回列表" }).click();
  await expect(page).toHaveURL(/\/reports$/);
});

test("header link 回顧 navigates to reports list", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "回顧" }).click();
  await expect(page).toHaveURL(/\/reports$/);
});
