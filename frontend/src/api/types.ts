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
  final_return_pct: number;
  mdd_pct: number;
  total_trades: number;
  win_rate_pct: number;
  total_fee: number;
  execution_time: number;
}

/** SSE 이벤트 타입 정의 */
export interface SSEPhaseEvent {
  phase: number;
  total: number;
  message: string;
}

export interface SSEProgressEvent {
  phase?: number;
  current: number;
  total: number;
  message?: string;
  date?: string;
}

export interface SSETradeEvent {
  date: string;
  side: "BUY" | "SELL";
  name: string;
  code: string;
  price?: number;
  quantity?: number;
  profit_pct?: number;
}

export interface SSELogEvent {
  message: string;
}

export interface SSEErrorEvent {
  message: string;
}

export type SSEEvent =
  | { type: "phase"; data: SSEPhaseEvent }
  | { type: "progress"; data: SSEProgressEvent }
  | { type: "trade"; data: SSETradeEvent }
  | { type: "log"; data: SSELogEvent }
  | { type: "error"; data: SSEErrorEvent }
  | { type: "result"; data: BacktestResult };
