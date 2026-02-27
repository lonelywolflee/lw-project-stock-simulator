import { AlertCircleIcon, TerminalIcon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { BacktestForm } from "@/components/forms/BacktestForm";
import { BacktestProgressLog } from "@/components/BacktestProgressLog";
import { BacktestResults } from "./BacktestResults";
import { useBacktestStream } from "@/hooks/useBacktestStream";
import type { BacktestParams } from "@/api/types";

export function BacktestDashboard() {
  const backtest = useBacktestStream();

  const handleSubmit = (params: BacktestParams) => {
    backtest.run(params);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      {/* 좌측 사이드바 - 파라미터 폼 */}
      <aside className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="font-display text-base font-bold">백테스트 설정</h2>
        </div>
        <BacktestForm
          onSubmit={handleSubmit}
          isLoading={backtest.isStreaming}
        />
      </aside>

      {/* 우측 메인 - 결과 영역 */}
      <main className="min-w-0 space-y-4">
        {/* 에러 알림 (스트림 외부 에러) */}
        {backtest.status === "error" && backtest.logs.length === 0 && (
          <Alert variant="destructive" className="border-destructive/30 bg-destructive/10">
            <AlertCircleIcon className="size-4" />
            <AlertTitle>실행 실패</AlertTitle>
            <AlertDescription>
              {backtest.error || "백테스트 실행 중 오류가 발생했습니다."}
            </AlertDescription>
          </Alert>
        )}

        {/* 진행 로그 */}
        {backtest.logs.length > 0 && (
          <BacktestProgressLog
            logs={backtest.logs}
            status={backtest.status}
          />
        )}

        {/* 결과 표시 */}
        {backtest.result && <BacktestResults result={backtest.result} />}

        {/* 초기 상태 */}
        {backtest.status === "idle" && (
          <div className="flex h-[400px] flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-border/50">
            <TerminalIcon className="size-8 text-muted-foreground/30" />
            <div className="text-center">
              <p className="text-sm text-muted-foreground">
                파라미터를 설정하고 백테스트를 실행하세요
              </p>
              <p className="mt-1 font-mono-data text-xs text-muted-foreground/50">
                READY
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
