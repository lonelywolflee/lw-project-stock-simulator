import { AlertCircleIcon, Loader2Icon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { BacktestForm } from "@/components/forms/BacktestForm";
import { BacktestResults } from "./BacktestResults";
import { useRunBacktest } from "@/hooks/useBacktest";
import type { BacktestParams } from "@/api/types";

export function BacktestDashboard() {
  const backtest = useRunBacktest();

  const handleSubmit = (params: BacktestParams) => {
    backtest.mutate(params);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      {/* 좌측 사이드바 - 파라미터 폼 */}
      <aside className="space-y-4">
        <h2 className="text-lg font-semibold">백테스트 설정</h2>
        <BacktestForm
          onSubmit={handleSubmit}
          isLoading={backtest.isPending}
        />
      </aside>

      {/* 우측 메인 - 결과 영역 */}
      <main className="min-w-0 space-y-4">
        {/* 에러 알림 */}
        {backtest.isError && (
          <Alert variant="destructive">
            <AlertCircleIcon className="size-4" />
            <AlertTitle>실행 실패</AlertTitle>
            <AlertDescription>
              {backtest.error?.message || "백테스트 실행 중 오류가 발생했습니다."}
            </AlertDescription>
          </Alert>
        )}

        {/* 로딩 스피너 */}
        {backtest.isPending && (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-8">
              <Loader2Icon className="size-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                백테스트 실행 중... 데이터 규모에 따라 수 분이 소요될 수 있습니다.
              </p>
            </CardContent>
          </Card>
        )}

        {/* 결과 표시 */}
        {backtest.data && <BacktestResults result={backtest.data} />}

        {/* 초기 상태 */}
        {!backtest.data && !backtest.isPending && !backtest.isError && (
          <div className="flex h-[400px] items-center justify-center rounded-lg border border-dashed">
            <p className="text-muted-foreground">
              왼쪽에서 파라미터를 설정하고 백테스트를 실행하세요.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
