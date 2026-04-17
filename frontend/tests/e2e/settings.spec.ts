import { test, expect, type Route } from "@playwright/test";

import stocksFixture from "./fixtures/stocks-list.json" with { type: "json" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/api/stocks?*", (route: Route) =>
    route.fulfill({ json: stocksFixture }),
  );
  await page.addInitScript(() => {
    window.localStorage.removeItem("alpha-lab:favorites");
    window.localStorage.removeItem("alpha-lab:tutorial-mode");
  });
});

test("settings page shows three sections", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "設定" })).toBeVisible();
  await expect(page.getByTestId("settings-tutorial")).toBeVisible();
  await expect(page.getByTestId("settings-favorites")).toBeVisible();
  await expect(page.getByTestId("settings-cache")).toBeVisible();
});

test("changing tutorial mode syncs with header toggle", async ({ page }) => {
  await page.goto("/settings");
  await page.getByTestId("tutorial-option-off").check();
  // Header toggle is a button with data-mode attribute
  await expect(page.getByTestId("tutorial-mode-toggle")).toHaveAttribute(
    "data-mode",
    "off",
  );
});

test("favorites from /stocks show up in settings and can be removed", async ({
  page,
}) => {
  await page.goto("/stocks");
  await page.getByTestId("fav-toggle-2330").click();
  await page.goto("/settings");
  await expect(page.getByTestId("favorite-row-2330")).toBeVisible();
  await page.getByTestId("favorite-remove-2330").click();
  await expect(page.getByTestId("favorite-row-2330")).not.toBeVisible();
});

test("cache section shows count and disables button when empty", async ({
  page,
}) => {
  await page.goto("/settings");
  await expect(page.getByTestId("cache-count")).toContainText("0");
  await expect(page.getByTestId("cache-clear")).toBeDisabled();
});
