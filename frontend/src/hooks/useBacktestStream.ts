import { useCallback, useRef, useState } from "react";
import { streamBacktest } from "@/api/client";
import type { BacktestParams, BacktestResult, SSEEvent } from "@/api/types";

export type LogEntryType = "phase" | "progress" | "trade" | "log" | "complete" | "error";

export interface LogEntry {
  id: number;
  type: LogEntryType;
  message: string;
  timestamp: Date;
  progress?: { current: number; total: number };
  tradeSide?: "BUY" | "SELL";
  profitPct?: number;
}

export type StreamStatus = "idle" | "streaming" | "done" | "error";

interface BacktestStreamState {
  status: StreamStatus;
  logs: LogEntry[];
  result: BacktestResult | null;
  error: string | null;
}

function formatKRW(value: number): string {
  return value.toLocaleString("ko-KR");
}

export function useBacktestStream() {
  const [state, setState] = useState<BacktestStreamState>({
    status: "idle",
    logs: [],
    result: null,
    error: null,
  });

  const idRef = useRef(0);

  const addLog = useCallback(
    (type: LogEntryType, message: string, extra?: Partial<LogEntry>) => {
      const entry: LogEntry = {
        id: ++idRef.current,
        type,
        message,
        timestamp: new Date(),
        ...extra,
      };
      setState((prev) => ({ ...prev, logs: [...prev.logs, entry] }));
    },
    [],
  );

  const updateLastProgress = useCallback(
    (message: string, progress: { current: number; total: number }) => {
      setState((prev) => {
        const logs = [...prev.logs];
        let lastIdx = -1;
        for (let i = logs.length - 1; i >= 0; i--) {
          if (logs[i].type === "progress") {
            lastIdx = i;
            break;
          }
        }
        if (lastIdx >= 0) {
          logs[lastIdx] = { ...logs[lastIdx], message, progress };
        } else {
          logs.push({
            id: ++idRef.current,
            type: "progress",
            message,
            timestamp: new Date(),
            progress,
          });
        }
        return { ...prev, logs };
      });
    },
    [],
  );

  const run = useCallback(
    async (params: BacktestParams) => {
      idRef.current = 0;
      setState({ status: "streaming", logs: [], result: null, error: null });

      const startTime = Date.now();

      try {
        await streamBacktest(params, (event: SSEEvent) => {
          switch (event.type) {
            case "phase":
              addLog(
                "phase",
                `[${event.data.phase}/${event.data.total}] ${event.data.message}`,
              );
              break;

            case "progress":
              updateLastProgress(event.data.message ?? event.data.date ?? "", {
                current: event.data.current,
                total: event.data.total,
              });
              break;

            case "trade": {
              const d = event.data;
              if (d.side === "BUY") {
                addLog(
                  "trade",
                  `  ↗ 매수: ${d.name} (${d.code}) — ${formatKRW(d.price!)}원 × ${d.quantity}주`,
                  { tradeSide: "BUY" },
                );
              } else {
                const sign = (d.profit_pct ?? 0) >= 0 ? "+" : "";
                addLog(
                  "trade",
                  `  ↘ 매도: ${d.name} (${d.code}) — ${sign}${d.profit_pct?.toFixed(1)}%`,
                  { tradeSide: "SELL", profitPct: d.profit_pct },
                );
              }
              break;
            }

            case "log":
              addLog("log", event.data.message);
              break;

            case "result": {
              const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
              const r = event.data;
              const sign = r.final_return_pct >= 0 ? "+" : "";
              addLog(
                "complete",
                `✓ 완료 — 총 ${r.total_trades}건 거래, 수익률 ${sign}${r.final_return_pct}% (${elapsed}초)`,
              );
              setState((prev) => ({
                ...prev,
                status: "done",
                result: event.data,
              }));
              break;
            }

            case "error":
              addLog("error", `✗ ${event.data.message}`);
              setState((prev) => ({
                ...prev,
                status: "error",
                error: event.data.message,
              }));
              break;
          }
        });

        // 스트림이 끝났는데 result 이벤트가 없었던 경우
        setState((prev) => {
          if (prev.status === "streaming") {
            return { ...prev, status: "error", error: "스트림이 예기치 않게 종료되었습니다" };
          }
          return prev;
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : "알 수 없는 오류";
        addLog("error", `✗ ${message}`);
        setState((prev) => ({
          ...prev,
          status: "error",
          error: message,
        }));
      }
    },
    [addLog, updateLastProgress],
  );

  return {
    ...state,
    run,
    isStreaming: state.status === "streaming",
    isDone: state.status === "done",
  };
}
