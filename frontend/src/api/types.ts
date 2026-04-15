export type JobType = "twse_prices" | "mops_revenue";

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
