import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, TerminalIcon } from "lucide-react";
import type { LogEntry, StreamStatus } from "@/hooks/useBacktestStream";

interface BacktestProgressLogProps {
  logs: LogEntry[];
  status: StreamStatus;
}

function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = total > 0 ? current / total : 0;
  const width = 24;
  const filled = Math.round(pct * width);
  const empty = width - filled;
  const bar = "\u2588".repeat(filled) + "\u2591".repeat(empty);
  const pctStr = (pct * 100).toFixed(1);

  return (
    <span className="text-muted-foreground">
      {"  "}
      <span className="text-mint/70">{bar}</span>{" "}
      {current}/{total} ({pctStr}%)
    </span>
  );
}

function LogLine({ entry }: { entry: LogEntry }) {
  const colorClass = (() => {
    switch (entry.type) {
      case "phase":
        return "text-mint";
      case "log":
        return "text-mint/80";
      case "complete":
        return "text-mint font-medium";
      case "error":
        return "text-destructive";
      case "trade":
        if (entry.tradeSide === "BUY") return "text-mint";
        if (entry.tradeSide === "SELL") {
          return (entry.profitPct ?? 0) >= 0
            ? "text-profit"
            : "text-loss";
        }
        return "text-foreground";
      default:
        return "text-foreground";
    }
  })();

  return (
    <div className="leading-relaxed">
      <span className={colorClass}>{entry.message}</span>
      {entry.type === "progress" && entry.progress && (
        <div>
          <ProgressBar
            current={entry.progress.current}
            total={entry.progress.total}
          />
        </div>
      )}
    </div>
  );
}

export function BacktestProgressLog({
  logs,
  status,
}: BacktestProgressLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isDone = status === "done" || status === "error";
  const [collapsed, setCollapsed] = useState(false);

  // 완료 시 자동 접기
  useEffect(() => {
    if (isDone) setCollapsed(true);
  }, [isDone]);

  // 자동 스크롤
  useEffect(() => {
    if (!collapsed && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, collapsed]);

  if (logs.length === 0) return null;

  return (
    <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
      {/* 헤더 */}
      <button
        type="button"
        onClick={() => isDone && setCollapsed((v) => !v)}
        className={`flex w-full items-center gap-2 px-4 py-2.5 text-left ${
          isDone
            ? "cursor-pointer hover:bg-accent/30"
            : "cursor-default"
        }`}
      >
        <TerminalIcon className="size-3.5 text-mint" />
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          실행 로그
        </span>
        {status === "streaming" && (
          <span className="ml-1 inline-block size-1.5 rounded-full bg-mint pulse-mint" />
        )}
        <span className="ml-auto">
          {isDone &&
            (collapsed ? (
              <ChevronRight className="size-3.5 text-muted-foreground" />
            ) : (
              <ChevronDown className="size-3.5 text-muted-foreground" />
            ))}
        </span>
      </button>

      {/* 로그 영역 */}
      {!collapsed && (
        <div
          ref={scrollRef}
          className="max-h-[300px] overflow-y-auto border-t border-border/30 bg-background/50 px-4 py-3 font-mono-data text-xs leading-relaxed"
        >
          {logs.map((entry) => (
            <LogLine key={entry.id} entry={entry} />
          ))}
          {status === "streaming" && (
            <span className="inline-block animate-pulse text-mint">&#x258A;</span>
          )}
        </div>
      )}
    </div>
  );
}
