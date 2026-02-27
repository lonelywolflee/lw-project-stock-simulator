"""FinanceDataReader 래퍼 모듈 - 주가 및 지수 데이터 수집.

DB 우선 조회 후 미스 시 네트워크 fetch -> DB 저장.
"""

import datetime
import logging
import time

import FinanceDataReader as fdr
import pandas as pd

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


def fetch_stock_listing(market: str = "KOSPI") -> pd.DataFrame:
    """상장 종목 목록을 반환한다.

    1. BatchMeta에서 오늘 fetch 했는지 확인
    2. 오늘 이미 fetch -> DB에서 조회
    3. fetch 안 함 -> FinanceDataReader 호출 -> DB 저장 -> BatchMeta 갱신
    4. 네트워크 실패 -> DB 기존 데이터 사용 (없으면 예외)
    """
    from apps.market_data.models import BatchMeta

    today = datetime.date.today()
    batch = BatchMeta.objects.filter(job_name=f"{market.lower()}_listing").first()

    if batch and batch.last_fetched_date == today:
        return _listing_from_db()

    try:
        df = _retry(fdr.StockListing, market)
        _save_listing_to_db(df)
        BatchMeta.objects.update_or_create(
            job_name=f"{market.lower()}_listing",
            defaults={"last_fetched_date": today},
        )
        return df
    except Exception:
        logger.warning("종목 목록 fetch 실패, DB fallback 시도")
        df = _listing_from_db()
        if df.empty:
            raise
        return df


def _listing_from_db() -> pd.DataFrame:
    """DB에서 종목 목록을 DataFrame으로 반환한다."""
    from apps.market_data.models import StockListing

    qs = StockListing.objects.all().values("code", "name", "market_cap")
    if not qs.exists():
        return pd.DataFrame(columns=["Code", "Name", "Marcap"])
    records = list(qs)
    return pd.DataFrame({
        "Code": [r["code"] for r in records],
        "Name": [r["name"] for r in records],
        "Marcap": [r["market_cap"] for r in records],
    })


def _save_listing_to_db(df: pd.DataFrame) -> None:
    """종목 목록 DataFrame을 DB에 upsert한다."""
    from apps.market_data.models import StockListing

    code_col = "Code" if "Code" in df.columns else "Symbol"
    cap_col = "Marcap" if "Marcap" in df.columns else "MarketCap"

    for _, row in df.iterrows():
        code = row.get(code_col, "")
        if not code:
            continue
        StockListing.objects.update_or_create(
            code=code,
            defaults={
                "name": row.get("Name", ""),
                "market_cap": int(row.get(cap_col, 0)) if row.get(cap_col) else None,
            },
        )


def fetch_price_data(code: str, start: str, end: str) -> pd.DataFrame:
    """개별 종목의 일별 가격 데이터를 반환한다. DB를 우선 확인한다."""
    df = _price_from_db(code, start, end)
    if df is not None and not df.empty:
        return df

    df = _retry(fdr.DataReader, code, start, end)
    if df is not None and not df.empty:
        _save_price_to_db(code, df, is_index=False)
        return df
    raise ValueError(f"{code} 가격 데이터를 가져올 수 없습니다 ({start}~{end})")


def fetch_all_prices(
    codes: list[str], start: str, end: str,
    progress_callback=None,
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
    df = _price_from_db("KS11", start, end)
    if df is not None and not df.empty:
        return df

    df = _retry(fdr.DataReader, "KS11", start, end)
    if df is not None and not df.empty:
        _save_price_to_db("KS11", df, is_index=True)
        return df
    raise ValueError(f"KOSPI 지수 데이터를 가져올 수 없습니다 ({start}~{end})")


def _price_from_db(code: str, start: str, end: str) -> pd.DataFrame | None:
    """DB에서 가격 데이터를 DataFrame으로 반환한다."""
    from apps.market_data.models import StockDailyPrice

    qs = StockDailyPrice.objects.filter(
        code=code, date__gte=start, date__lte=end,
    ).order_by("date").values("date", "open", "high", "low", "close", "volume")

    if not qs.exists():
        return None

    records = list(qs)
    df = pd.DataFrame(records)
    df.index = pd.to_datetime(df.pop("date"))
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df


def _save_price_to_db(code: str, df: pd.DataFrame, is_index: bool = False) -> None:
    """가격 DataFrame을 DB에 벌크 저장한다."""
    from apps.market_data.models import StockDailyPrice

    objects = []
    for date, row in df.iterrows():
        objects.append(StockDailyPrice(
            code=code,
            date=date.date() if hasattr(date, "date") else date,
            open=row["Open"],
            high=row["High"],
            low=row["Low"],
            close=row["Close"],
            volume=int(row.get("Volume", 0)),
            is_index=is_index,
        ))
    StockDailyPrice.objects.bulk_create(objects, ignore_conflicts=True)
