"""FinanceDataReader 래퍼 모듈 - 주가 및 지수 데이터 수집.

순수 데이터 수집 로직만 담당한다. DB 접근은 콜백으로 주입받는다.
"""

import logging
import re
import time
from collections.abc import Callable

import FinanceDataReader as fdr
import pandas as pd
import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds

FALLBACK_RETRIES = 1

LISTING_FALLBACK_MARKETS = {
    "KOSPI": "KOSPI-DESC",
    "KOSDAQ": "KOSDAQ-DESC",
}

INDEX_SYMBOLS = ["KOSPI", "NAVER:KOSPI"]


def _retry(func, *args, retries: int = MAX_RETRIES, **kwargs):
    """네트워크 요청을 지수 백오프로 재시도한다."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(args, kwargs)
            if attempt == retries - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Retry %d/%d after error: %s (waiting %.1fs)", attempt + 1, retries, e, delay)
            time.sleep(delay)


def _fetch_listing_with_fallback(market: str) -> pd.DataFrame:
    """목록 조회를 시도한다. 실패 시 DESC variant로 fallback."""
    try:
        return _retry(fdr.StockListing, market, retries=FALLBACK_RETRIES)
    except Exception as e:
        fallback = LISTING_FALLBACK_MARKETS.get(market)
        if fallback:
            logger.warning("종목 목록 %s 실패, %s로 fallback: %s", market, fallback, e)
            df = _retry(fdr.StockListing, fallback, retries=FALLBACK_RETRIES)
            return df[["Code", "Name"]]
        raise


def fetch_stock_listing(
    market: str = "KOSPI",
    *,
    is_batch_done: Callable[[], bool] | None = None,
    load_listing: Callable[[], pd.DataFrame | None] | None = None,
    save_listing: Callable[[pd.DataFrame], None] | None = None,
    mark_batch_done: Callable[[], None] | None = None,
) -> pd.DataFrame:
    """상장 종목 목록을 반환한다.

    1. is_batch_done()이 True면 load_listing()으로 DB 조회
    2. 아니면 FDR 호출 (KOSPI → KOSPI-DESC fallback) → save_listing() → mark_batch_done()
    3. 전체 실패 → load_listing() fallback (없으면 예외)
    """
    if is_batch_done and is_batch_done():
        df = load_listing() if load_listing else None
        if df is not None and not df.empty:
            return df

    try:
        df = _fetch_listing_with_fallback(market)
        if save_listing:
            save_listing(df)
        if mark_batch_done:
            mark_batch_done()
        return df
    except Exception:
        logger.warning("종목 목록 fetch 실패, DB fallback 시도")
        df = load_listing() if load_listing else None
        if df is not None and not df.empty:
            return df
        raise


def fetch_price_data(
    code: str, start: str, end: str,
    *,
    load_price: Callable[[str, str, str], pd.DataFrame | None] | None = None,
    save_price: Callable[[str, pd.DataFrame, bool], None] | None = None,
) -> pd.DataFrame:
    """개별 종목의 일별 가격 데이터를 반환한다.

    load_price로 저장소 조회 후 미스 시 네트워크 fetch → save_price로 저장.
    """
    if load_price:
        df = load_price(code, start, end)
        if df is not None and not df.empty:
            return df

    df = _retry(fdr.DataReader, code, start, end)
    if df is not None and not df.empty:
        if save_price:
            save_price(code, df, False)
        return df
    raise ValueError(f"{code} 가격 데이터를 가져올 수 없습니다 ({start}~{end})")


def fetch_price_data_raw(code: str, start: str, end: str) -> pd.DataFrame:
    """네트워크에서 가격 데이터를 fetch한다. 빈 결과도 허용한다.

    증분 캐시의 sub-range fetch 시 사용. ValueError를 발생시키지 않는다.
    """
    df = _retry(fdr.DataReader, code, start, end)
    if df is not None and not df.empty:
        return df
    return pd.DataFrame()


def fetch_all_prices(
    codes: list[str], start: str, end: str,
    *,
    progress_callback: Callable[[int, int], None] | None = None,
    load_price: Callable[[str, str, str], pd.DataFrame | None] | None = None,
    save_price: Callable[[str, pd.DataFrame, bool], None] | None = None,
) -> dict[str, pd.DataFrame]:
    """여러 종목의 가격 데이터를 딕셔너리로 반환한다."""
    result: dict[str, pd.DataFrame] = {}
    for i, code in enumerate(codes):
        try:
            df = fetch_price_data(
                code, start, end,
                load_price=load_price, save_price=save_price,
            )
            if df is not None and not df.empty:
                result[code] = df
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", code, e)
        if progress_callback:
            progress_callback(i + 1, len(codes))
    return result


def _fetch_index_with_fallback(start: str, end: str) -> pd.DataFrame:
    """지수 데이터를 fetch한다. 실패 시 fallback 심볼로 재시도."""
    for i, symbol in enumerate(INDEX_SYMBOLS):
        try:
            df = _retry(fdr.DataReader, symbol, start, end, retries=FALLBACK_RETRIES)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            if i < len(INDEX_SYMBOLS) - 1:
                logger.warning("지수 %s 실패, %s로 fallback: %s", symbol, INDEX_SYMBOLS[i + 1], e)
            else:
                raise
    return pd.DataFrame()


def fetch_kospi_index(
    start: str, end: str,
    *,
    load_price: Callable[[str, str, str], pd.DataFrame | None] | None = None,
    save_price: Callable[[str, pd.DataFrame, bool], None] | None = None,
) -> pd.DataFrame:
    """KOSPI 지수 데이터를 반환한다."""
    if load_price:
        df = load_price("KOSPI", start, end)
        if df is not None and not df.empty:
            return df

    df = _fetch_index_with_fallback(start, end)
    if df is not None and not df.empty:
        if save_price:
            save_price("KOSPI", df, True)
        return df
    raise ValueError(f"KOSPI 지수 데이터를 가져올 수 없습니다 ({start}~{end})")


def fetch_listing_shares_from_naver(code: str) -> int | None:
    """네이버 증권에서 상장주식수를 스크래핑한다."""
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    try:
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0",
        })
        r.raise_for_status()
    except Exception:
        logger.warning("네이버 증권 %s 요청 실패", code)
        return None

    match = re.search(
        r"상장주식수</th>\s*<td[^>]*><em>([\d,]+)</em>",
        r.text,
    )
    if not match:
        logger.warning("네이버 증권 %s 상장주식수 파싱 실패", code)
        return None

    return int(match.group(1).replace(",", ""))


if __name__ == "__main__":
    df = fetch_stock_listing("KOSPI")
    print(df)
#     df = fetch_price_data("NAVER:481850", "2023-01-02", "2025-01-02")
#     print(df)
#     df = fetch_kospi_index("2024-01-02", "2024-01-04")
#     print(df)
#     df = fetch_all_prices(["005930", "000660"], "2024-01-02", "2024-01-04")
#     print(df)