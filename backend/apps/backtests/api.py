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
    username = request.user.username if request.user.is_authenticated else ""
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
                username=username,
            )
            kospi_index = fetch_kospi_index(bp.start_date, bp.end_date, username=username)
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
