# 백테스트 실시간 진행 로그 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 백테스트 실행 중 터미널 스타일 실시간 진행 로그를 SSE로 스트리밍하여 사용자에게 보여준다.

**Architecture:** 기존 동기 POST 엔드포인트를 SSE(Server-Sent Events) 스트리밍으로 교체한다. 백엔드는 Django `StreamingHttpResponse`로 진행 이벤트를 push하고, 프론트엔드는 `fetch` + `ReadableStream`으로 소비한다. 백그라운드 스레드 + Queue 패턴으로 데이터 수집/시뮬레이션 중 실시간 이벤트를 전달한다.

**Tech Stack:** Django StreamingHttpResponse, threading + queue (stdlib), fetch ReadableStream API, React custom hook, Tailwind CSS

**Design doc:** `docs/plans/2026-02-26-backtest-progress-log-design.md`

---

### Task 1: Backend SSE 유틸리티

SSE 이벤트 포맷 헬퍼 함수를 만든다.

**Files:**
- Create: `backend/apps/backtests/sse.py`
- Create: `backend/tests/test_sse.py`

**Step 1: 테스트 작성**

`backend/tests/test_sse.py`:
```python
"""SSE 포맷 유틸리티 테스트."""

from apps.backtests.sse import format_sse


class TestFormatSSE:
    def test_basic_event(self):
        result = format_sse("phase", {"phase": 1, "message": "로딩 중..."})
        assert result == 'event: phase\ndata: {"phase": 1, "message": "\\ub85c\\ub529 \\uc911..."}\n\n'

    def test_event_contains_newlines(self):
        """SSE 이벤트는 반드시 \\n\\n 으로 끝나야 한다."""
        result = format_sse("progress", {"current": 1, "total": 10})
        assert result.endswith("\n\n")

    def test_event_has_correct_prefix(self):
        result = format_sse("trade", {"side": "BUY"})
        lines = result.strip().split("\n")
        assert lines[0] == "event: trade"
        assert lines[1].startswith("data: ")

    def test_data_is_valid_json(self):
        import json
        result = format_sse("result", {"value": 42})
        data_line = result.strip().split("\n")[1]
        payload = data_line[len("data: "):]
        parsed = json.loads(payload)
        assert parsed == {"value": 42}
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator/backend && python -m pytest tests/test_sse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.backtests.sse'`

**Step 3: 구현**

`backend/apps/backtests/sse.py`:
```python
"""SSE (Server-Sent Events) 포맷 유틸리티."""

import json


def format_sse(event_type: str, data: dict) -> str:
    """SSE 이벤트 문자열을 생성한다.

    Args:
        event_type: 이벤트 타입 (phase, progress, trade, result, error)
        data: JSON 직렬화할 데이터 딕셔너리

    Returns:
        SSE 포맷 문자열 ("event: ...\ndata: ...\n\n")
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"
```

**Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator/backend && python -m pytest tests/test_sse.py -v`
Expected: 4 passed

**Step 5: 커밋**

```bash
git add apps/backtests/sse.py tests/test_sse.py
git commit -m "feat: SSE 포맷 유틸리티 추가"
```

---

### Task 2: 백테스트 엔진 이벤트 콜백

`run_backtest`의 `progress_callback`을 이벤트 딕셔너리 기반 `event_callback`으로 변경하여 매매 이벤트도 보고한다.

**Files:**
- Modify: `backend/core/engine/backtest.py:139-242`
- Modify: `backend/tests/test_backtest.py`

**Step 1: 콜백 테스트 추가**

`backend/tests/test_backtest.py` 끝에 추가:
```python
    def test_event_callback_reports_progress_and_trades(self):
        """event_callback이 progress와 trade 이벤트를 보고해야 한다."""
        prices = [100, 101, 102, 103, 102, 101, 100]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-12",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days=3,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        events = []
        result = run_backtest(params, price_data, listing, event_callback=events.append)

        # progress 이벤트가 있어야 함
        progress_events = [e for e in events if e["type"] == "progress"]
        assert len(progress_events) > 0

        # 매매가 발생했으면 trade 이벤트도 있어야 함
        if result.total_trades > 0:
            trade_events = [e for e in events if e["type"] == "trade"]
            assert len(trade_events) > 0

        # progress 이벤트에 필수 필드 확인
        p = progress_events[0]
        assert "current" in p
        assert "total" in p
        assert "date" in p
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator/backend && python -m pytest tests/test_backtest.py::TestRunBacktest::test_event_callback_reports_progress_and_trades -v`
Expected: FAIL — `TypeError` (unexpected keyword argument `event_callback`)

**Step 3: 엔진 수정**

`backend/core/engine/backtest.py` — `run_backtest` 함수를 수정한다:

1. 파라미터명 변경: `progress_callback` → `event_callback`
2. progress 호출 변경
3. 매매 이벤트 추가

수정 사항:

함수 시그니처 (line 139-145):
```python
def run_backtest(
    params: BacktestParams,
    price_data: dict[str, pd.DataFrame],
    listing_df: pd.DataFrame | None = None,
    kospi_df: pd.DataFrame | None = None,
    event_callback=None,
) -> BacktestResult:
```

docstring의 `progress_callback: (current, total) 콜백` → `event_callback: 이벤트 딕셔너리 콜백`

SELL phase 내부 — `portfolio.sell_all()` 호출 후 (line 196 부근), 매도 성공 시 이벤트 전송:
```python
        for code in codes_to_sell:
            if code not in price_data or date not in price_data[code].index:
                continue
            price = price_data[code].loc[date, "Close"]
            name = name_map.get(code, code)
            holding = portfolio.holdings.get(code)
            avg_price = holding.avg_price if holding else price
            if portfolio.sell_all(date_str, code, name, price):
                if event_callback:
                    profit_pct = round((price - avg_price) / avg_price * 100, 1) if avg_price > 0 else 0.0
                    event_callback({
                        "type": "trade",
                        "side": "SELL",
                        "date": date_str,
                        "name": name,
                        "code": code,
                        "price": price,
                        "profit_pct": profit_pct,
                    })
```

BUY phase 내부 — `portfolio.buy()` 호출 후 (line 221 부근), 매수 성공 시 이벤트 전송:
```python
        for code, name, price in buy_candidates:
            if portfolio.cash < params.min_balance:
                break
            if portfolio.buy(date_str, code, name, price,
                             params.max_buy_amount, params.min_balance):
                if event_callback:
                    # 방금 매수한 거래 정보
                    last_trade = portfolio.trades[-1]
                    event_callback({
                        "type": "trade",
                        "side": "BUY",
                        "date": date_str,
                        "name": name,
                        "code": code,
                        "price": price,
                        "quantity": last_trade.quantity,
                    })
```

SNAPSHOT 이후 progress 호출 변경 (line 231-232):
```python
        if event_callback:
            event_callback({
                "type": "progress",
                "current": day_idx + 1,
                "total": total_days,
                "date": date_str,
            })
```

**주의:** 기존 SELL phase에서 `portfolio.sell_all()` 리턴값을 사용하지 않았다. `sell_all`은 bool을 반환하므로, 반환값을 체크하도록 수정한다. 또한 매도 전에 `holding.avg_price`를 저장해야 한다 (매도 후에는 holding이 삭제됨).

**Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator/backend && python -m pytest tests/test_backtest.py -v`
Expected: ALL passed (기존 테스트 + 새 테스트)

**Step 5: 커밋**

```bash
git add core/engine/backtest.py tests/test_backtest.py
git commit -m "feat: 백테스트 엔진에 event_callback 추가 (매매 이벤트 보고)"
```

---

### Task 3: Backend SSE 스트리밍 엔드포인트

기존 동기 엔드포인트를 SSE 스트리밍으로 교체한다. Thread + Queue 패턴 사용.

**Files:**
- Modify: `backend/apps/backtests/api.py` (전체 교체)

**Step 1: 엔드포인트 교체**

`backend/apps/backtests/api.py` 전체를 다음으로 교체:
```python
"""백테스트 API — SSE 스트리밍 엔드포인트."""

import logging
import queue
import threading
import time

from django.http import StreamingHttpResponse
from ninja import Router

from core.data.fetcher import (
    fetch_all_prices,
    fetch_kospi_index,
    fetch_stock_listing,
)
from core.engine.backtest import BacktestParams, run_backtest

from .schemas import BacktestParamsSchema
from .serializers import serialize_result
from .sse import format_sse

logger = logging.getLogger(__name__)

router = Router()

PROGRESS_BATCH_SIZE = 10  # 주가 수집 진행률 이벤트 전송 주기


@router.post("/run")
def run(request, params: BacktestParamsSchema):
    """백테스트 실행 (SSE 스트리밍) — 진행 이벤트를 실시간으로 전송한다."""
    bp = BacktestParams(**params.dict())
    event_queue: queue.Queue = queue.Queue()

    def worker():
        try:
            start_time = time.time()

            # ── Phase 1: 종목 목록 로딩 ──
            event_queue.put(("phase", {
                "phase": 1, "total": 4,
                "message": "종목 목록 로딩 중...",
            }))
            listing = fetch_stock_listing("KOSPI")
            codes = listing["Code"].tolist()
            event_queue.put(("log", {
                "message": f"✓ KOSPI {len(codes)}개 종목 로드",
            }))

            # ── Phase 2: 주가 데이터 수집 ──
            event_queue.put(("phase", {
                "phase": 2, "total": 4,
                "message": "주가 데이터 수집 중...",
            }))

            def on_data_progress(current, total):
                if current % PROGRESS_BATCH_SIZE == 0 or current == total:
                    event_queue.put(("progress", {
                        "phase": 2,
                        "current": current,
                        "total": total,
                        "message": "주가 데이터 수집 중...",
                    }))

            prices = fetch_all_prices(
                codes, bp.start_date, bp.end_date,
                progress_callback=on_data_progress,
            )
            kospi_index = fetch_kospi_index(bp.start_date, bp.end_date)
            event_queue.put(("log", {
                "message": f"✓ {len(prices)}개 종목 데이터 수집 완료",
            }))

            # ── Phase 3: 시뮬레이션 실행 ──
            event_queue.put(("phase", {
                "phase": 3, "total": 4,
                "message": "시뮬레이션 실행 중...",
            }))

            def on_backtest_event(event):
                event_queue.put((event["type"], event))

            result = run_backtest(
                bp, prices, listing, kospi_index,
                event_callback=on_backtest_event,
            )

            # ── Phase 4: 결과 생성 ──
            event_queue.put(("phase", {
                "phase": 4, "total": 4,
                "message": "결과 생성 중...",
            }))
            execution_time = round(time.time() - start_time, 2)
            serialized = serialize_result(result)
            serialized["execution_time"] = execution_time

            event_queue.put(("result", serialized))

        except Exception as e:
            logger.exception("Backtest SSE stream error")
            event_queue.put(("error", {"message": str(e)}))
        finally:
            event_queue.put(None)  # sentinel

    def event_stream():
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        while True:
            try:
                item = event_queue.get(timeout=120)
            except queue.Empty:
                yield format_sse("error", {"message": "타임아웃: 응답이 없습니다"})
                break

            if item is None:
                break

            event_type, data = item
            yield format_sse(event_type, data)

        thread.join(timeout=5)

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
```

**Step 2: 수동 테스트**

1. Django 서버 실행: `cd backend && python manage.py runserver`
2. curl로 SSE 확인:
```bash
curl -N -X POST http://localhost:8000/api/backtests/run \
  -H "Content-Type: application/json" \
  -d '{"initial_cash":10000000,"start_date":"2024-01-01","end_date":"2024-01-31","fee_rate":0.015,"n_rise_days":3,"m_fall_days":3,"y_emergency_pct":5.0,"max_buy_amount":5000000,"min_balance":1000000,"sort_method":"market_cap"}'
```
Expected: SSE 이벤트가 순차적으로 출력됨

**Step 3: 커밋**

```bash
git add apps/backtests/api.py
git commit -m "feat: 백테스트 API를 SSE 스트리밍으로 교체"
```

---

### Task 4: Frontend SSE 타입 + 클라이언트

SSE 이벤트 타입을 정의하고, fetch + ReadableStream 기반 스트리밍 클라이언트를 구현한다.

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`

**Step 1: SSE 이벤트 타입 추가**

`frontend/src/api/types.ts` 파일 끝에 추가:
```typescript

/** SSE 이벤트 타입 정의 */
export interface SSEPhaseEvent {
  phase: number;
  total: number;
  message: string;
}

export interface SSEProgressEvent {
  phase: number;
  current: number;
  total: number;
  message: string;
}

export interface SSETradeEvent {
  phase: number;
  date: string;
  side: "BUY" | "SELL";
  name: string;
  code: string;
  price?: number;
  quantity?: number;
  profit_pct?: number;
}

export interface SSELogEvent {
  message: string;
}

export interface SSEErrorEvent {
  message: string;
}

export type SSEEvent =
  | { type: "phase"; data: SSEPhaseEvent }
  | { type: "progress"; data: SSEProgressEvent }
  | { type: "trade"; data: SSETradeEvent }
  | { type: "log"; data: SSELogEvent }
  | { type: "error"; data: SSEErrorEvent }
  | { type: "result"; data: BacktestResult };
```

**Step 2: 스트리밍 클라이언트 구현**

`frontend/src/api/client.ts` 전체를 다음으로 교체:
```typescript
import type { BacktestParams, SSEEvent } from "./types";

/** SSE 원시 텍스트를 파싱한다. */
function parseSSE(raw: string): SSEEvent | null {
  let eventType = "message";
  const dataLines: string[] = [];

  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  const dataStr = dataLines.join("\n");
  if (!dataStr) return null;

  try {
    return { type: eventType, data: JSON.parse(dataStr) } as SSEEvent;
  } catch {
    return null;
  }
}

/** 백테스트를 SSE 스트리밍으로 실행한다. */
export async function streamBacktest(
  params: BacktestParams,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const response = await fetch("/api/backtests/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop()!;

    for (const chunk of chunks) {
      if (!chunk.trim()) continue;
      const event = parseSSE(chunk);
      if (event) onEvent(event);
    }
  }

  if (buffer.trim()) {
    const event = parseSSE(buffer);
    if (event) onEvent(event);
  }
}
```

**Step 3: 커밋**

```bash
cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator
git add frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat: SSE 이벤트 타입 정의 및 스트리밍 클라이언트 구현"
```

---

### Task 5: Frontend `useBacktestStream` 훅

SSE 이벤트를 소비하여 로그, 진행률, 결과를 관리하는 React 커스텀 훅을 만든다.

**Files:**
- Create: `frontend/src/hooks/useBacktestStream.ts`
- Delete: `frontend/src/hooks/useBacktest.ts`

**Step 1: 훅 구현**

`frontend/src/hooks/useBacktestStream.ts`:
```typescript
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
        const lastIdx = logs.findLastIndex((l) => l.type === "progress");
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
              updateLastProgress(event.data.message, {
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
```

**Step 2: 기존 훅 삭제**

`frontend/src/hooks/useBacktest.ts` 파일을 삭제한다.

**Step 3: 커밋**

```bash
cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator
git add frontend/src/hooks/useBacktestStream.ts
git rm frontend/src/hooks/useBacktest.ts
git commit -m "feat: useBacktestStream 훅 구현 및 기존 훅 교체"
```

---

### Task 6: Frontend `BacktestProgressLog` 컴포넌트

터미널 스타일 로그 UI 컴포넌트를 만든다.

**Files:**
- Create: `frontend/src/components/BacktestProgressLog.tsx`

**Step 1: 컴포넌트 구현**

`frontend/src/components/BacktestProgressLog.tsx`:
```tsx
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
  const bar = "█".repeat(filled) + "░".repeat(empty);
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
        if (entry.tradeSide === "BUY") return "text-profit";
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
            <span className="inline-block animate-pulse text-mint">▊</span>
          )}
        </div>
      )}
    </div>
  );
}
```

**Step 2: 커밋**

```bash
cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator
git add frontend/src/components/BacktestProgressLog.tsx
git commit -m "feat: 터미널 스타일 BacktestProgressLog 컴포넌트 추가"
```

---

### Task 7: Dashboard 통합 및 정리

`BacktestDashboard`에 새 훅과 로그 컴포넌트를 연결하고 기존 로딩 스피너를 교체한다.

**Files:**
- Modify: `frontend/src/features/backtest/BacktestDashboard.tsx`

**Step 1: Dashboard 수정**

`frontend/src/features/backtest/BacktestDashboard.tsx` 전체를 다음으로 교체:
```tsx
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
```

**Step 2: Vite 프록시 확인**

`frontend/vite.config.ts`의 `/api` 프록시 설정 확인. `fetch` + `ReadableStream`은 기본 프록시 설정으로 동작해야 한다. 만약 SSE 이벤트가 한꺼번에 도착하는 경우, 다음 설정 추가 필요:

```typescript
"/api": {
  target: "http://localhost:8000",
  changeOrigin: true,
  configure: (proxy) => {
    proxy.on("proxyRes", (proxyRes) => {
      if (proxyRes.headers["content-type"]?.includes("text/event-stream")) {
        proxyRes.headers["cache-control"] = "no-cache";
        proxyRes.headers["connection"] = "keep-alive";
      }
    });
  },
},
```

**Step 3: 통합 테스트**

1. 백엔드 실행: `cd backend && python manage.py runserver`
2. 프론트엔드 실행: `cd frontend && npm run dev`
3. 브라우저에서 백테스트 실행:
   - 로그 영역이 나타나고 이벤트가 순차적으로 표시되는지 확인
   - 프로그레스바가 업데이트되는지 확인
   - 매매 이벤트가 색상과 함께 표시되는지 확인
   - 완료 시 로그가 접히고 결과 차트/테이블이 표시되는지 확인
   - 접힌 로그를 클릭하면 다시 펼쳐지는지 확인

**Step 4: 커밋**

```bash
cd /Users/hoan.lee/Private/lonelywolf/lw-project-stock-simulator
git add frontend/src/features/backtest/BacktestDashboard.tsx
git commit -m "feat: BacktestDashboard에 실시간 진행 로그 통합"
```
