import { ClockIcon } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
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
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline" className="text-xs">
          완료
        </Badge>
        {result.execution_time > 0 && (
          <span className="flex items-center gap-1">
            <ClockIcon className="size-3" />
            {formatExecutionTime(result.execution_time)}
          </span>
        )}
      </div>

      {/* 핵심 지표 카드 */}
      <MetricsCards result={result} />

      {/* 탭 (자산 추이 / 벤치마크 비교 / 거래 내역) */}
      <Tabs defaultValue="asset">
        <TabsList>
          <TabsTrigger value="asset">자산 추이</TabsTrigger>
          <TabsTrigger value="comparison">벤치마크 비교</TabsTrigger>
          <TabsTrigger value="trades">
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
          <div className="rounded-lg border">
            <TradeTable trades={result.trades} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
