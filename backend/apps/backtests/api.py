"""백테스트 API — 동기 단일 엔드포인트."""

import logging
import time

from ninja import Router

from core.data.fetcher import (
    fetch_all_prices,
    fetch_exchange_rate,
    fetch_kospi_index,
    fetch_nasdaq_index,
    fetch_stock_listing,
)
from core.engine.backtest import (
    BacktestParams,
    run_backtest,
    run_dual_market_backtest,
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
    ratio = bp.kospi_ratio / 100.0

    # ── 1. 데이터 로딩 ──
    kospi_listing = None
    kospi_codes: list[str] = []
    if ratio > 0:
        kospi_listing = fetch_stock_listing("KOSPI")
        kospi_codes = kospi_listing["Code"].tolist()

    nasdaq_listing = None
    nasdaq_codes: list[str] = []
    if ratio < 1:
        nasdaq_listing = fetch_stock_listing("NASDAQ")
        nasdaq_codes = nasdaq_listing["Symbol"].tolist()

    kospi_prices = (
        fetch_all_prices(kospi_codes, bp.start_date, bp.end_date)
        if kospi_codes
        else {}
    )
    nasdaq_prices = (
        fetch_all_prices(nasdaq_codes, bp.start_date, bp.end_date)
        if nasdaq_codes
        else {}
    )

    kospi_index = (
        fetch_kospi_index(bp.start_date, bp.end_date) if ratio > 0 else None
    )
    nasdaq_index = (
        fetch_nasdaq_index(bp.start_date, bp.end_date) if ratio < 1 else None
    )
    exchange_rate = (
        fetch_exchange_rate(bp.start_date, bp.end_date) if ratio < 1 else None
    )

    # ── 2. 백테스트 실행 ──
    if ratio == 1.0:
        result = run_backtest(bp, kospi_prices, kospi_listing, kospi_index)
    elif ratio == 0.0:
        result = run_backtest(bp, nasdaq_prices, nasdaq_listing, nasdaq_index)
    else:
        result = run_dual_market_backtest(
            bp,
            kospi_prices,
            nasdaq_prices,
            kospi_listing,
            nasdaq_listing,
            kospi_index,
            nasdaq_index,
            exchange_rate,
        )

    # ── 3. 결과 반환 ──
    execution_time = round(time.time() - start_time, 2)
    serialized = serialize_result(result)
    serialized["execution_time"] = execution_time

    logger.info("Backtest completed in %.2fs", execution_time)
    return serialized
