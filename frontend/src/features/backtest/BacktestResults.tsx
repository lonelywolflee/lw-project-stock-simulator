import { CheckCircleIcon, ClockIcon } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MetricsCards } from "@/components/metrics/MetricsCards";
import { AssetChart } from "@/components/charts/AssetChart";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import { TradeTable } from "@/components/tables/TradeTable";
import type { BacktestResult } from "@/api/types";
import { formatExecutionTime } from "@/utils/formatters";

interface BacktestResultsProps {
  result: BacktestResult;
}

export function BacktestResults({ result }: BacktestResultsProps) {
  return (
    <div className="space-y-4">
      {/* 실행 정보 */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5 rounded-full border border-mint/20 bg-mint/5 px-2.5 py-1 text-mint">
          <CheckCircleIcon className="size-3" />
          <span className="font-mono-data text-[11px] font-medium uppercase">완료</span>
        </div>
        {result.execution_time > 0 && (
          <span className="flex items-center gap-1 font-mono-data">
            <ClockIcon className="size-3" />
            {formatExecutionTime(result.execution_time)}
          </span>
        )}
      </div>

      {/* 핵심 지표 카드 */}
      <MetricsCards result={result} />

      {/* 탭 (자산 추이 / 벤치마크 비교 / 거래 내역) */}
      <Tabs defaultValue="asset">
        <TabsList className="border border-border/50 bg-card">
          <TabsTrigger value="asset" className="font-mono-data text-xs">
            자산 추이
          </TabsTrigger>
          <TabsTrigger value="comparison" className="font-mono-data text-xs">
            벤치마크 비교
          </TabsTrigger>
          <TabsTrigger value="trades" className="font-mono-data text-xs">
            거래 내역 ({result.total_trades})
          </TabsTrigger>
        </TabsList>
        <TabsContent value="asset" className="mt-4">
          <AssetChart snapshots={result.daily_snapshots} />
        </TabsContent>
        <TabsContent value="comparison" className="mt-4">
          <ComparisonChart result={result} />
        </TabsContent>
        <TabsContent value="trades" className="mt-4">
          <div className="rounded-lg border border-border/60">
            <TradeTable trades={result.trades} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
