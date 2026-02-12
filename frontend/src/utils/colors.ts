/** 금융 차트/테이블 색상 유틸리티. */

/** 한국 금융 컨벤션: 상승=빨강, 하락=파랑 */
export const PROFIT_COLOR = "hsl(0, 72%, 51%)";
export const LOSS_COLOR = "hsl(221, 83%, 53%)";
export const NEUTRAL_COLOR = "hsl(0, 0%, 50%)";

/** 차트 색상 팔레트 */
export const CHART_COLORS = {
  cash: "hsl(142, 71%, 45%)",
  stockValue: "hsl(221, 83%, 53%)",
  totalValue: "hsl(0, 72%, 51%)",
  portfolio: "hsl(262, 83%, 58%)",
  kospi: "hsl(0, 72%, 51%)",
  nasdaq: "hsl(221, 83%, 53%)",
} as const;

/** 차트 색상 (투명도 포함) */
export const CHART_FILL_COLORS = {
  cash: "hsla(142, 71%, 45%, 0.3)",
  stockValue: "hsla(221, 83%, 53%, 0.3)",
  totalValue: "hsla(0, 72%, 51%, 0.1)",
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
