import axios from "axios";
import type { BacktestParams, BacktestResult } from "./types";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
  timeout: 600_000,
});

export async function runBacktest(
  params: BacktestParams,
): Promise<BacktestResult> {
  const { data } = await api.post<BacktestResult>("/backtests/run", params);
  return data;
}
