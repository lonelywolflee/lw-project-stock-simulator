/** 금융 차트/테이블 색상 유틸리티. */

/** 한국 금융 컨벤션: 상승=빨강, 하락=파랑 */
export const PROFIT_COLOR = "#ff4757";
export const LOSS_COLOR = "#3b82f6";
export const NEUTRAL_COLOR = "#8e8ea8";

/** 차트 색상 팔레트 (다크 테마) */
export const CHART_COLORS = {
  cash: "#00d4aa",
  stockValue: "#5b7fff",
  totalValue: "#ff4757",
  portfolio: "#a855f7",
  kospi: "#ff4757",
} as const;

/** 차트 색상 (투명도 포함) */
export const CHART_FILL_COLORS = {
  cash: "rgba(0, 212, 170, 0.2)",
  stockValue: "rgba(91, 127, 255, 0.2)",
  totalValue: "rgba(255, 71, 87, 0.05)",
} as const;

export function getProfitColor(value: number): string {
  if (value > 0) return PROFIT_COLOR;
  if (value < 0) return LOSS_COLOR;
  return NEUTRAL_COLOR;
}

export function getProfitClass(value: number): string {
  if (value > 0) return "text-profit";
  if (value < 0) return "text-loss";
  return "text-muted-foreground";
}
