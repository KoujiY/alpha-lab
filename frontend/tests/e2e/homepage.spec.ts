import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test("載入首頁並顯示標題", async ({ page }) => {
    // Mock health API so this E2E doesn't need backend running
    await page.route("**/api/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          version: "0.1.0",
          timestamp: new Date().toISOString(),
        }),
      });
    });

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "alpha-lab" })).toBeVisible();
    await expect(page.getByText("Phase 0 骨架運作中")).toBeVisible();
  });

  test("後端連線成功時顯示綠色狀態", async ({ page }) => {
    await page.route("**/api/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          version: "0.1.0",
          timestamp: new Date().toISOString(),
        }),
      });
    });

    await page.goto("/");
    await expect(page.getByText(/後端連線正常/)).toBeVisible();
  });

  test("後端失敗時顯示錯誤訊息", async ({ page }) => {
    await page.route("**/api/health", async (route) => {
      await route.abort("failed");
    });

    await page.goto("/");
    await expect(page.getByText(/後端連線失敗/)).toBeVisible();
  });
});
