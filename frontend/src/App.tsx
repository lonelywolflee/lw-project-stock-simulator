import { LineChartIcon } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { BacktestDashboard } from "@/features/backtest/BacktestDashboard";

function App() {
  return (
    <div className="min-h-screen bg-background">
      {/* 헤더 */}
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-6">
          <LineChartIcon className="size-5 text-primary" />
          <h1 className="text-base font-bold tracking-tight">
            Stock Simulator
          </h1>
          <span className="text-xs text-muted-foreground">
            KOSPI + NASDAQ 이중 시장 백테스트
          </span>
        </div>
      </header>

      <Separator />

      {/* 메인 콘텐츠 */}
      <div className="mx-auto max-w-7xl px-6 py-6">
        <BacktestDashboard />
      </div>
    </div>
  );
}

export default App;
