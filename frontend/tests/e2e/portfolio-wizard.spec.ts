import { test, expect, type Route } from "@playwright/test";

const meta = {
  symbol: "2330",
  name: "台積電",
  industry: "半導體",
  listed_date: null,
};

const overview = {
  meta,
  prices: [],
  revenues: [],
  financials: [],
  institutional: [],
  margin: [],
  events: [],
};

const baseMeta = {
  id: 42,
  style: "balanced",
  label: "主力組合",
  note: null,
  base_date: "2026-04-17",
  created_at: "2026-04-17T00:00:00Z",
  holdings_count: 2,
  parent_id: null,
  parent_nav_at_fork: null,
};

const baseDetail = {
  ...baseMeta,
  holdings: [
    { symbol: "2317", name: "鴻海", weight: 0.6, base_price: 100 },
    { symbol: "2303", name: "聯電", weight: 0.4, base_price: 50 },
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/api/stocks/2330/overview", (route: Route) =>
    route.fulfill({ json: overview }),
  );
  await page.route("**/api/stocks/2330/score", (route: Route) =>
    route.fulfill({ json: { symbol: "2330", latest: null } }),
  );
  await page.route("**/api/reports?*", (route: Route) =>
    route.fulfill({ json: [] }),
  );
});

test("wizard two-step flow: pick base → preview weights → save", async ({
  page,
}) => {
  const captured: Array<Record<string, unknown>> = [];

  await page.route("**/api/portfolios/saved", (route: Route) => {
    const req = route.request();
    if (req.method() === "GET") return route.fulfill({ json: [baseMeta] });
    if (req.method() === "POST") {
      captured.push(req.postDataJSON() as Record<string, unknown>);
      return route.fulfill({ json: { ...baseMeta, id: 99 } });
    }
    return route.fallback();
  });
  await page.route("**/api/portfolios/saved/42", (route: Route) =>
    route.fulfill({ json: baseDetail }),
  );
  await page.route("**/api/portfolios/saved/probe*", (route: Route) =>
    route.fulfill({
      json: {
        target_date: "2026-04-17",
        resolved_date: "2026-04-17",
        today_available: true,
        missing_today_symbols: [],
        symbol_statuses: {},
      },
    }),
  );

  await page.goto("/stocks/2330");
  await page.getByTestId("add-to-portfolio").click();
  await expect(page.getByTestId("wizard-step-1")).toBeVisible();

  await page.getByTestId("pick-portfolio-42").click();
  await expect(page.getByTestId("wizard-step-2")).toBeVisible();
  await expect(page.getByTestId("wizard-sum")).toContainText("100.00%");

  // preview shows the merged rows (2317, 2303, and new 2330)
  await expect(page.getByTestId("wizard-row-2317")).toBeVisible();
  await expect(page.getByTestId("wizard-row-2303")).toBeVisible();
  await expect(page.getByTestId("wizard-row-2330")).toBeVisible();

  // manually edit 2330 to 25%
  await page.getByTestId("wizard-weight-input-2330").fill("25");
  // sum stays at 100% (others re-normalize)
  await expect(page.getByTestId("wizard-sum")).toContainText("100.00%");

  await page.getByTestId("wizard-confirm").click();
  await expect.poll(() => captured.length).toBeGreaterThan(0);
  expect(captured[0]?.parent_id).toBe(42);
});

test("wizard shows soft-limit warning when weight exceeds 40%", async ({
  page,
}) => {
  await page.route("**/api/portfolios/saved", (route: Route) =>
    route.fulfill({ json: [baseMeta] }),
  );
  await page.route("**/api/portfolios/saved/42", (route: Route) =>
    route.fulfill({ json: baseDetail }),
  );

  await page.goto("/stocks/2330");
  await page.getByTestId("add-to-portfolio").click();
  await page.getByTestId("pick-portfolio-42").click();
  await expect(page.getByTestId("wizard-step-2")).toBeVisible();

  // push 2317 to 60% → over the 40% threshold
  await page.getByTestId("wizard-weight-input-2317").fill("60");
  await expect(
    page.getByTestId("wizard-warning-single_weight_too_high"),
  ).toBeVisible();
  // Confirm button still enabled (soft limits do not block)
  await expect(page.getByTestId("wizard-confirm")).toBeEnabled();
});

test("wizard back button returns to step 1", async ({ page }) => {
  await page.route("**/api/portfolios/saved", (route: Route) =>
    route.fulfill({ json: [baseMeta] }),
  );
  await page.route("**/api/portfolios/saved/42", (route: Route) =>
    route.fulfill({ json: baseDetail }),
  );

  await page.goto("/stocks/2330");
  await page.getByTestId("add-to-portfolio").click();
  await page.getByTestId("pick-portfolio-42").click();
  await expect(page.getByTestId("wizard-step-2")).toBeVisible();
  await page.getByTestId("wizard-back").click();
  await expect(page.getByTestId("wizard-step-1")).toBeVisible();
});
