"""백테스트 API — 동기 단일 엔드포인트."""

import logging
import time

from ninja import Router

from core.data.fetcher import (
    fetch_all_prices,
    fetch_kospi_index,
    fetch_stock_listing,
)
from core.engine.backtest import (
    BacktestParams,
    run_backtest,
)

from .schemas import BacktestParamsSchema, BacktestResultSchema
from .serializers import serialize_result

logger = logging.getLogger(__name__)

router = Router()


@router.post("/run", response=BacktestResultSchema)
def run(request, params: BacktestParamsSchema):
    """백테스트 실행 (동기) — 데이터 수집 → 엔진 실행 → 결과 반환."""
    start_time = time.time()

    bp = BacktestParams(**params.dict())

    # ── 1. 데이터 로딩 ──
    kospi_listing = fetch_stock_listing("KOSPI")
    kospi_codes = kospi_listing["Code"].tolist()
    kospi_prices = fetch_all_prices(kospi_codes, bp.start_date, bp.end_date)
    kospi_index = fetch_kospi_index(bp.start_date, bp.end_date)

    # ── 2. 백테스트 실행 ──
    result = run_backtest(bp, kospi_prices, kospi_listing, kospi_index)

    # ── 3. 결과 반환 ──
    execution_time = round(time.time() - start_time, 2)
    serialized = serialize_result(result)
    serialized["execution_time"] = execution_time

    logger.info("Backtest completed in %.2fs", execution_time)
    return serialized
