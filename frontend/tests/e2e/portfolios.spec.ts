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

// 建一個會觸發 soft-limit 的推薦 fixture：單檔權重 60% > 40% threshold
const heavyFixture = {
  generated_at: "2026-04-15T20:00:00Z",
  calc_date: "2026-04-15",
  portfolios: [
    {
      style: "aggressive" as const,
      label: "積極組",
      is_top_pick: false,
      holdings: [
        {
          symbol: "2330",
          name: "台積電",
          weight: 0.6,
          score_breakdown: {
            symbol: "2330",
            calc_date: "2026-04-15",
            value_score: 60,
            growth_score: 70,
            dividend_score: 80,
            quality_score: 90,
            total_score: 80,
          },
          reasons: ["積極組：集中押注高成長。"],
        },
        {
          symbol: "2454",
          name: "聯發科",
          weight: 0.4,
          score_breakdown: {
            symbol: "2454",
            calc_date: "2026-04-15",
            value_score: 70,
            growth_score: 80,
            dividend_score: 60,
            quality_score: 75,
            total_score: 71,
          },
          reasons: ["積極組：次要成長。"],
        },
      ],
      expected_yield: 5.0,
      risk_score: 60,
      reasoning_ref: null,
    },
  ],
};

test("儲存此組合：單檔 60% 觸發 soft-limit，按取消不送出", async ({ page }) => {
  await page.route("**/api/portfolios/recommend**", (route: Route) =>
    route.fulfill({ json: heavyFixture }),
  );
  let probeCalled = false;
  let postCalled = false;
  await page.route("**/api/portfolios/saved/probe*", (route: Route) => {
    probeCalled = true;
    return route.fulfill({
      json: {
        target_date: "2026-04-15",
        resolved_date: "2026-04-15",
        today_available: true,
        missing_today_symbols: [],
        symbol_statuses: {},
      },
    });
  });
  await page.route("**/api/portfolios/saved", (route: Route) => {
    if (route.request().method() === "POST") {
      postCalled = true;
      return route.fulfill({
        json: {
          id: 1,
          style: "aggressive",
          label: "積極組 2026-04-15",
          note: null,
          base_date: "2026-04-15",
          created_at: "2026-04-15T00:00:00Z",
          holdings_count: 2,
          parent_id: null,
          parent_nav_at_fork: null,
        },
      });
    }
    return route.fulfill({ json: [] });
  });

  await page.goto("/portfolios");
  await page.getByTestId("save-portfolio-button").click();

  const dlg = page.getByTestId("soft-limit-dialog");
  await expect(dlg).toBeVisible();
  await expect(
    page.getByTestId("wizard-warning-single_weight_too_high"),
  ).toBeVisible();

  await page.getByTestId("soft-limit-cancel").click();
  await expect(dlg).not.toBeVisible();
  expect(probeCalled).toBe(false);
  expect(postCalled).toBe(false);
});

test("儲存此組合：soft-limit 警告按「仍要儲存」會繼續走 probe + save", async ({
  page,
}) => {
  await page.route("**/api/portfolios/recommend**", (route: Route) =>
    route.fulfill({ json: heavyFixture }),
  );
  let probeCalled = false;
  const postBodies: Array<Record<string, unknown>> = [];
  await page.route("**/api/portfolios/saved/probe*", (route: Route) => {
    probeCalled = true;
    return route.fulfill({
      json: {
        target_date: "2026-04-15",
        resolved_date: "2026-04-15",
        today_available: true,
        missing_today_symbols: [],
        symbol_statuses: {},
      },
    });
  });
  await page.route("**/api/portfolios/saved", (route: Route) => {
    const req = route.request();
    if (req.method() === "POST") {
      postBodies.push(req.postDataJSON() as Record<string, unknown>);
      return route.fulfill({
        json: {
          id: 2,
          style: "aggressive",
          label: "積極組 2026-04-15",
          note: null,
          base_date: "2026-04-15",
          created_at: "2026-04-15T00:00:00Z",
          holdings_count: 2,
          parent_id: null,
          parent_nav_at_fork: null,
        },
      });
    }
    return route.fulfill({ json: [] });
  });

  await page.goto("/portfolios");
  await page.getByTestId("save-portfolio-button").click();
  await expect(page.getByTestId("soft-limit-dialog")).toBeVisible();
  await page.getByTestId("soft-limit-proceed").click();

  await expect.poll(() => postBodies.length).toBeGreaterThan(0);
  expect(probeCalled).toBe(true);
  const holdings = postBodies[0]?.holdings as Array<{ symbol: string; weight: number }>;
  expect(holdings[0].symbol).toBe("2330");
  expect(holdings[0].weight).toBeCloseTo(0.6, 5);
});
