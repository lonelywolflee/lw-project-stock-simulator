/** 백테스트 API 요청/응답 TypeScript 타입 정의. */

export interface BacktestParams {
  initial_cash: number;
  start_date: string;
  end_date: string;
  fee_rate: number;
  n_rise_days: number;
  m_fall_days: number;
  y_emergency_pct: number;
  max_buy_amount: number;
  min_balance: number;
  sort_method: "market_cap" | "return_rate";
  kospi_ratio: number;
}

export interface Trade {
  date: string;
  code: string;
  name: string;
  side: string;
  price: number;
  quantity: number;
  amount: number;
  fee: number;
  profit: number;
  market: string;
}

export interface DailySnapshot {
  date: string;
  cash: number;
  stock_value: number;
  total_value: number;
}

export interface MarketIndex {
  dates: string[];
  values: number[];
}

export interface BacktestResult {
  daily_snapshots: DailySnapshot[];
  trades: Trade[];
  kospi_index: MarketIndex | null;
  nasdaq_index: MarketIndex | null;
  initial_exchange_rate: number;
  kospi_snapshots: DailySnapshot[];
  nasdaq_snapshots: DailySnapshot[];
  final_return_pct: number;
  mdd_pct: number;
  total_trades: number;
  win_rate_pct: number;
  total_fee: number;
  execution_time: number;
}
