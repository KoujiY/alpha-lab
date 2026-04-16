export type JobType = "twse_prices" | "twse_prices_batch" | "mops_revenue";

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface JobResponse {
  id: number;
  job_type: string;
  status: JobStatus;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface JobCreateRequest {
  type: JobType;
  params: Record<string, unknown>;
}

export interface StockMeta {
  symbol: string;
  name: string;
  industry: string | null;
  listed_date: string | null;
}

export interface DailyPricePoint {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface RevenuePoint {
  year: number;
  month: number;
  revenue: number;
  yoy_growth: number | null;
  mom_growth: number | null;
}

export interface FinancialPoint {
  period: string;
  revenue: number | null;
  gross_profit: number | null;
  operating_income: number | null;
  net_income: number | null;
  eps: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  total_equity: number | null;
}

export interface InstitutionalPoint {
  trade_date: string;
  foreign_net: number;
  trust_net: number;
  dealer_net: number;
  total_net: number;
}

export interface MarginPoint {
  trade_date: string;
  margin_balance: number;
  margin_buy: number;
  margin_sell: number;
  short_balance: number;
  short_sell: number;
  short_cover: number;
}

export interface EventPoint {
  id: number;
  event_datetime: string;
  event_type: string;
  title: string;
  content: string;
}

export interface StockOverview {
  meta: StockMeta;
  prices: DailyPricePoint[];
  revenues: RevenuePoint[];
  financials: FinancialPoint[];
  institutional: InstitutionalPoint[];
  margin: MarginPoint[];
  events: EventPoint[];
}

export interface GlossaryTerm {
  term: string;
  short: string;
  detail: string;
  related: string[];
}

export interface FactorBreakdown {
  symbol: string;
  calc_date: string;
  value_score: number | null;
  growth_score: number | null;
  dividend_score: number | null;
  quality_score: number | null;
  total_score: number | null;
}

export interface ScoreResponse {
  symbol: string;
  latest: FactorBreakdown | null;
}

export type PortfolioStyle = "conservative" | "balanced" | "aggressive";

export interface Holding {
  symbol: string;
  name: string;
  weight: number;
  score_breakdown: FactorBreakdown;
  reasons: string[];
}

export interface Portfolio {
  style: PortfolioStyle;
  label: string;
  is_top_pick: boolean;
  holdings: Holding[];
  expected_yield: number | null;
  risk_score: number | null;
  reasoning_ref: string | null;
}

export interface RecommendResponse {
  generated_at: string;
  calc_date: string;
  portfolios: Portfolio[];
}

export interface L2TopicMeta {
  id: string;
  title: string;
  related_terms: string[];
}

export interface L2Topic extends L2TopicMeta {
  body_markdown: string;
}

export type ReportType = "stock" | "portfolio" | "events" | "research";

export interface ReportMeta {
  id: string;
  type: ReportType;
  title: string;
  symbols: string[];
  tags: string[];
  date: string;
  path: string;
  summary_line: string;
  starred: boolean;
}

export interface ReportDetail extends ReportMeta {
  body_markdown: string;
}

// --- Screener ---

export interface FactorMeta {
  key: string;
  label: string;
  min_value: number;
  max_value: number;
  default_min: number;
  description: string;
}

export interface FactorsResponse {
  factors: FactorMeta[];
}

export interface FactorRange {
  key: string;
  min_value: number;
  max_value: number;
}

export interface ScreenerStock {
  symbol: string;
  name: string;
  industry: string | null;
  value_score: number | null;
  growth_score: number | null;
  dividend_score: number | null;
  quality_score: number | null;
  total_score: number | null;
}

export interface FilterResponse {
  calc_date: string;
  total_count: number;
  stocks: ScreenerStock[];
}

// --- Saved Portfolios (Phase 6) ---

export interface SavedHolding {
  symbol: string;
  name: string;
  weight: number;
  base_price: number;
}

export interface SavedPortfolioCreate {
  style: PortfolioStyle;
  label: string;
  note?: string | null;
  holdings: SavedHolding[];
}

export interface SavedPortfolioMeta {
  id: number;
  style: PortfolioStyle;
  label: string;
  note: string | null;
  base_date: string;
  created_at: string;
  holdings_count: number;
}

export interface SavedPortfolioDetail extends SavedPortfolioMeta {
  holdings: SavedHolding[];
}

export interface PerformancePoint {
  date: string;
  nav: number;
  daily_return: number | null;
}

export interface PerformanceResponse {
  portfolio: SavedPortfolioDetail;
  points: PerformancePoint[];
  latest_nav: number;
  total_return: number;
}

export interface BaseDateProbe {
  target_date: string;
  resolved_date: string | null;
  today_available: boolean;
  missing_today_symbols: string[];
}
