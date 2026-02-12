import {
  TrendingUpIcon,
  TrendingDownIcon,
  BarChart3Icon,
  TargetIcon,
  WalletIcon,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
    },
    {
      label: "최대 낙폭 (MDD)",
      value: formatPercent(-result.mdd_pct),
      icon: TrendingDownIcon,
      colorClass: "text-loss",
    },
    {
      label: "총 거래 횟수",
      value: `${formatNumber(result.total_trades)}회`,
      icon: BarChart3Icon,
      colorClass: "text-foreground",
    },
    {
      label: "승률",
      value: formatPercent(result.win_rate_pct).replace("+", ""),
      icon: TargetIcon,
      colorClass:
        result.win_rate_pct >= 50 ? "text-profit" : "text-muted-foreground",
    },
    {
      label: "총 수수료",
      value: formatKRW(result.total_fee),
      icon: WalletIcon,
      colorClass: "text-muted-foreground",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      {metrics.map((m) => (
        <Card key={m.label}>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-muted p-2">
              <m.icon className="size-4 text-muted-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground truncate">
                {m.label}
              </p>
              <p className={`text-lg font-bold tabular-nums ${m.colorClass}`}>
                {m.value}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
