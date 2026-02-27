import {
  TrendingUpIcon,
  TrendingDownIcon,
  BarChart3Icon,
  TargetIcon,
  WalletIcon,
} from "lucide-react";
import type { BacktestResult } from "@/api/types";
import { formatPercent, formatNumber, formatKRW } from "@/utils/formatters";
import { getProfitClass } from "@/utils/colors";

interface MetricsCardsProps {
  result: BacktestResult;
}

export function MetricsCards({ result }: MetricsCardsProps) {
  const metrics = [
    {
      label: "총 수익률",
      value: formatPercent(result.final_return_pct),
      icon: result.final_return_pct >= 0 ? TrendingUpIcon : TrendingDownIcon,
      colorClass: getProfitClass(result.final_return_pct),
      highlight: true,
    },
    {
      label: "최대 낙폭 (MDD)",
      value: formatPercent(-result.mdd_pct),
      icon: TrendingDownIcon,
      colorClass: "text-loss",
      highlight: false,
    },
    {
      label: "총 거래 횟수",
      value: `${formatNumber(result.total_trades)}회`,
      icon: BarChart3Icon,
      colorClass: "text-foreground",
      highlight: false,
    },
    {
      label: "승률",
      value: formatPercent(result.win_rate_pct).replace("+", ""),
      icon: TargetIcon,
      colorClass:
        result.win_rate_pct >= 50 ? "text-profit" : "text-muted-foreground",
      highlight: false,
    },
    {
      label: "총 수수료",
      value: formatKRW(result.total_fee),
      icon: WalletIcon,
      colorClass: "text-muted-foreground",
      highlight: false,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
      {metrics.map((m) => (
        <div
          key={m.label}
          className={`group relative overflow-hidden rounded-lg border border-border/60 bg-card p-3 transition-colors hover:border-border ${
            m.highlight ? "glow-mint-sm border-mint/20" : ""
          }`}
        >
          <div className="mb-2 flex items-center gap-2">
            <m.icon className="size-3.5 text-muted-foreground" />
            <span className="truncate text-[11px] uppercase tracking-wider text-muted-foreground">
              {m.label}
            </span>
          </div>
          <p className={`font-mono-data text-xl font-bold ${m.colorClass}`}>
            {m.value}
          </p>
        </div>
      ))}
    </div>
  );
}
