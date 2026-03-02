"""백테스트 API — SSE 스트리밍 엔드포인트."""

import logging
import queue
import threading
import time

from django.http import StreamingHttpResponse
from ninja import Router

from apps.market_data.services import (
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

            has_marcap = "Marcap" in listing.columns
            if has_marcap:
                event_queue.put(("log", {
                    "message": f"✓ KOSPI {len(codes)}개 종목 로드",
                }))
            else:
                event_queue.put(("log", {
                    "message": f"⚠ KOSPI 목록 조회 실패로 KOSPI-DESC를 사용합니다. "
                               f"{len(codes)}개 종목 로드 (실시간 시가총액 미반영)",
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
            if not has_marcap and bp.sort_method == "market_cap":
                event_queue.put(("log", {
                    "message": "⚠ 시가총액 정보가 없는 종목은 거래대금(거래량×종가) 기준으로 산정합니다.",
                }))

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
            logger.info("Backtest completed in %.2fs", execution_time)

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
