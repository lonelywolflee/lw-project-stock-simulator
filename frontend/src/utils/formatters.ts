/** 한국 금융 서비스용 숫자/날짜 포맷터. */

const krwFormatter = new Intl.NumberFormat("ko-KR", {
  style: "currency",
  currency: "KRW",
  maximumFractionDigits: 0,
});

const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat("ko-KR");

const compactFormatter = new Intl.NumberFormat("ko-KR", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatKRW(value: number): string {
  return krwFormatter.format(value);
}

export function formatUSD(value: number): string {
  return usdFormatter.format(value);
}

export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

export function formatCompact(value: number): string {
  return compactFormatter.format(value);
}

export function formatPercent(value: number, decimals = 2): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatPercentUnsigned(value: number, decimals = 2): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function formatCurrency(value: number, market: string): string {
  return market === "NASDAQ" ? formatUSD(value) : formatKRW(value);
}

export function formatExecutionTime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}초`;
  const min = Math.floor(seconds / 60);
  const sec = (seconds % 60).toFixed(0);
  return `${min}분 ${sec}초`;
}
