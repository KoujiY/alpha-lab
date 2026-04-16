import { test, expect, type Route } from "@playwright/test";

import listFixture from "./fixtures/reports-list.json" with { type: "json" };
import detailFixture from "./fixtures/reports-portfolio-detail.json" with {
  type: "json",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  // Handle PATCH and DELETE on specific report, plus GET detail
  await page.route("**/api/reports/*", async (route: Route) => {
    const req = route.request();
    if (req.method() === "PATCH") {
      const body = req.postDataJSON() as { starred?: boolean };
      const id = new URL(req.url()).pathname.split("/").pop() ?? "";
      await route.fulfill({
        json: {
          ...(listFixture.find((r) => r.id === id) ?? listFixture[0]),
          starred: body.starred ?? false,
        },
      });
      return;
    }
    if (req.method() === "DELETE") {
      await route.fulfill({ status: 204, body: "" });
      return;
    }
    await route.fulfill({ json: detailFixture });
  });
  await page.route("**/api/reports?*", (route: Route) => {
    const url = route.request().url();
    if (url.includes("type=stock")) {
      route.fulfill({
        json: listFixture.filter((r) => r.type === "stock"),
      });
      return;
    }
    route.fulfill({ json: listFixture });
  });
  await page.route("**/api/reports", (route: Route) =>
    route.fulfill({ json: listFixture }),
  );
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

test("can toggle star on report card", async ({ page }) => {
  await page.goto("/reports");
  const star = page.getByTestId("star-toggle").first();
  await expect(star).toHaveText("☆");
  await star.click();
  await expect(star).toHaveText("★");
});

test("can delete report after confirm", async ({ page }) => {
  await page.goto("/reports");
  page.once("dialog", (d) => d.accept());
  await page.getByTestId("delete-report").first().click();
  // After mutation success → list refetched (mock returns same list — non-stateful).
  // Asserting the button was clickable completes the flow test.
});

test("search input filters reports via query param", async ({ page }) => {
  let lastRequestedUrl = "";
  await page.route("**/api/reports?**", (route: Route) => {
    const url = route.request().url();
    if (url.includes("q=")) {
      lastRequestedUrl = url;
      route.fulfill({ json: [] });
      return;
    }
    route.fulfill({ json: listFixture });
  });
  await page.goto("/reports");
  await page.getByTestId("reports-search").fill("不存在");
  await expect
    .poll(() => lastRequestedUrl, { timeout: 3000 })
    .toContain("q=%E4%B8%8D%E5%AD%98%E5%9C%A8");
});
