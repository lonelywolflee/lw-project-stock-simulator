"""FinanceDataReader 래퍼 모듈 - 주가 및 지수 데이터 수집."""

import time
import logging

import FinanceDataReader as fdr
import pandas as pd

from src.data.cache import load_from_cache, save_to_cache

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


def _retry(func, *args, retries: int = MAX_RETRIES, **kwargs):
    """네트워크 요청을 지수 백오프로 재시도한다."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Retry %d/%d after error: %s (waiting %.1fs)", attempt + 1, retries, e, delay)
            time.sleep(delay)


def fetch_stock_listing() -> pd.DataFrame:
    """KOSPI 상장 종목 목록을 반환한다."""
    return _retry(fdr.StockListing, "KOSPI")


def fetch_price_data(code: str, start: str, end: str) -> pd.DataFrame:
    """개별 종목의 일별 가격 데이터를 반환한다. 캐시를 우선 확인한다."""
    cached = load_from_cache(code, start, end)
    if cached is not None:
        return cached

    df = _retry(fdr.DataReader, code, start, end)
    if df is not None and not df.empty:
        save_to_cache(code, start, end, df)
    return df


def fetch_all_prices(
    codes: list[str], start: str, end: str, progress_callback=None
) -> dict[str, pd.DataFrame]:
    """여러 종목의 가격 데이터를 딕셔너리로 반환한다."""
    result: dict[str, pd.DataFrame] = {}
    for i, code in enumerate(codes):
        try:
            df = fetch_price_data(code, start, end)
            if df is not None and not df.empty:
                result[code] = df
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", code, e)
        if progress_callback:
            progress_callback(i + 1, len(codes))
    return result


def fetch_kospi_index(start: str, end: str) -> pd.DataFrame:
    """KOSPI 지수(KS11) 데이터를 반환한다."""
    cached = load_from_cache("KS11", start, end)
    if cached is not None:
        return cached

    df = _retry(fdr.DataReader, "KS11", start, end)
    if df is not None and not df.empty:
        save_to_cache("KS11", start, end, df)
    return df
