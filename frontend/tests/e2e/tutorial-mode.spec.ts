import { test, expect } from "@playwright/test";

test.describe("Tutorial mode toggle", () => {
  test.beforeEach(async ({ page }) => {
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
    // Playwright 每個 test 有獨立 browser context，localStorage 預設即為空，
    // 不需手動清理（否則 addInitScript 會在 reload 時再次清掉，打壞持久化測試）。
  });

  test("cycles full -> compact -> off and persists on reload", async ({
    page,
  }) => {
    await page.goto("/");
    const toggle = page.getByTestId("tutorial-mode-toggle");
    await expect(toggle).toHaveAttribute("data-mode", "full");

    await toggle.click();
    await expect(toggle).toHaveAttribute("data-mode", "compact");

    await toggle.click();
    await expect(toggle).toHaveAttribute("data-mode", "off");

    await page.reload();
    await expect(page.getByTestId("tutorial-mode-toggle")).toHaveAttribute(
      "data-mode",
      "off",
    );

    // 再點一下循環回 full
    await page.getByTestId("tutorial-mode-toggle").click();
    await expect(page.getByTestId("tutorial-mode-toggle")).toHaveAttribute(
      "data-mode",
      "full",
    );
  });

  test("label reflects current mode", async ({ page }) => {
    await page.goto("/");
    const toggle = page.getByTestId("tutorial-mode-toggle");
    await expect(toggle).toContainText("完整教學");
    await toggle.click();
    await expect(toggle).toContainText("精簡");
    await toggle.click();
    await expect(toggle).toContainText("關閉");
  });
});
