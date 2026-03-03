"""시장 데이터 서비스 — 증분 캐시 오케스트레이션.

PriceFetchCoverage로 일자별 커버리지를 추적하여,
미캐시 범위만 네트워크에서 fetch하고 DB에 저장한다.
종목 목록은 BatchMeta로 하루 1회 배치 관리한다.
"""

import datetime
import logging

import pandas as pd

from core.data.fetcher import (
    _fetch_index_with_fallback as _core_fetch_index_with_fallback,
    fetch_listing_shares_from_naver as _fetch_listing_shares_from_naver,
    fetch_price_data_raw as _core_fetch_price_data_raw,
    fetch_stock_listing as _core_fetch_stock_listing,
)

from .models import BatchMeta, PriceFetchCoverage, StockDailyPrice, StockListing

logger = logging.getLogger(__name__)


# ── 종목 목록 DB 콜백 ──────────────────────────────────────────


def _is_listing_batch_done(market: str) -> bool:
    batch = BatchMeta.objects.filter(job_name=f"{market.lower()}_listing").first()
    return batch is not None and batch.last_fetched_date == datetime.date.today()


def _load_listing_from_db(market: str) -> pd.DataFrame | None:
    records = list(
        StockListing.objects.filter(market=market).values("code", "name", "listing_shares")
    )
    if not records:
        return None
    return pd.DataFrame({
        "Code": [r["code"] for r in records],
        "Name": [r["name"] for r in records],
        "Stocks": [r["listing_shares"] for r in records],
    })


def _save_listing_to_db(market: str, df: pd.DataFrame) -> None:
    code_col = "Code" if "Code" in df.columns else "Symbol"
    shares_col = "Stocks" if "Stocks" in df.columns else "ListingShares"
    has_shares = shares_col in df.columns

    objects = []
    for _, row in df.iterrows():
        code = row.get(code_col, "")
        if not code:
            continue
        objects.append(StockListing(
            market=market,
            code=code,
            name=row.get("Name", ""),
            listing_shares=int(row.get(shares_col, 0)) if has_shares and row.get(shares_col) else None,
            listing_shares_updated_at=datetime.date.today() if has_shares and row.get(shares_col) else None,
        ))

    update_fields = ["name"]
    if has_shares:
        update_fields.extend(["listing_shares", "listing_shares_updated_at"])

    StockListing.objects.bulk_create(
        objects,
        update_conflicts=True,
        unique_fields=["market", "code"],
        update_fields=update_fields,
    )


def _mark_listing_batch_done(market: str) -> None:
    BatchMeta.objects.update_or_create(
        job_name=f"{market.lower()}_listing",
        defaults={"last_fetched_date": datetime.date.today()},
    )


def resolve_listing_shares(market: str, code: str) -> int | None:
    """DB 캐시를 확인하고, 미스 시 네이버에서 상장주식수를 가져온다."""
    obj = StockListing.objects.filter(market=market, code=code).first()
    if not obj:
        return None

    if obj.listing_shares_updated_at == datetime.date.today():
        return obj.listing_shares

    shares = _fetch_listing_shares_from_naver(code)
    if shares is not None:
        obj.listing_shares = shares
    obj.listing_shares_updated_at = datetime.date.today()
    obj.save(update_fields=["listing_shares", "listing_shares_updated_at"])
    return shares


# ── 가격 데이터 DB 콜백 ────────────────────────────────────────


def _find_uncovered_ranges(market: str, code: str, start: str, end: str) -> list[tuple[str, str]]:
    """커버리지 테이블에서 미캐시 연속 날짜 범위를 반환한다."""
    start_date = datetime.date.fromisoformat(start)
    end_date = datetime.date.fromisoformat(end)

    all_dates: set[datetime.date] = set()
    current = start_date
    while current <= end_date:
        all_dates.add(current)
        current += datetime.timedelta(days=1)

    covered_dates = set(
        PriceFetchCoverage.objects.filter(
            market=market, code=code, date__gte=start_date, date__lte=end_date,
        ).values_list("date", flat=True)
    )

    uncovered = sorted(all_dates - covered_dates)
    if not uncovered:
        return []

    ranges: list[tuple[str, str]] = []
    range_start = uncovered[0]
    prev = uncovered[0]
    for d in uncovered[1:]:
        if (d - prev).days > 1:
            ranges.append((str(range_start), str(prev)))
            range_start = d
        prev = d
    ranges.append((str(range_start), str(prev)))
    return ranges


def _save_coverage(market: str, code: str, start: str, end: str, fetched_df: pd.DataFrame) -> None:
    """fetch한 범위의 모든 날짜에 대해 커버리지를 기록한다."""
    start_date = datetime.date.fromisoformat(start)
    end_date = datetime.date.fromisoformat(end)

    if fetched_df is not None and not fetched_df.empty:
        data_dates = {
            d.date() if hasattr(d, "date") else d for d in fetched_df.index
        }
    else:
        data_dates = set()

    objects = []
    current = start_date
    while current <= end_date:
        objects.append(PriceFetchCoverage(
            market=market, code=code, date=current, has_data=current in data_dates,
        ))
        current += datetime.timedelta(days=1)

    PriceFetchCoverage.objects.bulk_create(objects, ignore_conflicts=True)


def _load_price_from_db(market: str, code: str, start: str, end: str) -> pd.DataFrame | None:
    """DB에서 가격 데이터를 로드한다."""
    records = list(
        StockDailyPrice.objects.filter(
            market=market, code=code, date__gte=start, date__lte=end,
        ).order_by("date").values("date", "open", "high", "low", "close", "volume")
    )
    if not records:
        return None

    df = pd.DataFrame(records)
    df.index = pd.to_datetime(df.pop("date"))
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df


def _save_price_to_db(market: str, code: str, df: pd.DataFrame, is_index: bool = False) -> None:
    objects = []
    for date, row in df.iterrows():
        objects.append(StockDailyPrice(
            market=market,
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


# ── 공개 API (DB 콜백이 주입된 fetcher) ────────────────────────


def fetch_stock_listing(market: str = "KOSPI") -> pd.DataFrame:
    """상장 종목 목록을 반환한다 (DB 배치 관리 포함)."""
    return _core_fetch_stock_listing(
        market,
        is_batch_done=lambda: _is_listing_batch_done(market),
        load_listing=lambda: _load_listing_from_db(market),
        save_listing=lambda df: _save_listing_to_db(market, df),
        mark_batch_done=lambda: _mark_listing_batch_done(market),
    )


def fetch_price_data(code: str, start: str, end: str, *, market: str = "KOSPI") -> pd.DataFrame:
    """개별 종목의 일별 가격 데이터를 반환한다 (증분 캐시)."""
    uncovered = _find_uncovered_ranges(market, code, start, end)

    for r_start, r_end in uncovered:
        df = _core_fetch_price_data_raw(code, r_start, r_end)
        if df is not None and not df.empty:
            _save_price_to_db(market, code, df, False)
        _save_coverage(market, code, r_start, r_end, df)

    df = _load_price_from_db(market, code, start, end)
    if df is not None and not df.empty:
        return df
    raise ValueError(f"{code} 가격 데이터를 가져올 수 없습니다 ({start}~{end})")


def fetch_all_prices(
    codes: list[str], start: str, end: str,
    progress_callback=None,
    *,
    market: str = "KOSPI",
) -> dict[str, pd.DataFrame]:
    """여러 종목의 가격 데이터를 딕셔너리로 반환한다 (증분 캐시)."""
    result: dict[str, pd.DataFrame] = {}
    for i, code in enumerate(codes):
        try:
            df = fetch_price_data(code, start, end, market=market)
            if df is not None and not df.empty:
                result[code] = df
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", code, e)
        if progress_callback:
            progress_callback(i + 1, len(codes))
    return result


def fetch_kospi_index(start: str, end: str) -> pd.DataFrame:
    """KOSPI 지수 데이터를 반환한다 (증분 캐시)."""
    market = "KOSPI"
    code = "KOSPI"
    uncovered = _find_uncovered_ranges(market, code, start, end)

    for r_start, r_end in uncovered:
        df = _core_fetch_index_with_fallback(r_start, r_end)
        if df is not None and not df.empty:
            _save_price_to_db(market, code, df, True)
        _save_coverage(market, code, r_start, r_end, df)

    df = _load_price_from_db(market, code, start, end)
    if df is not None and not df.empty:
        return df
    raise ValueError(f"KOSPI 지수 데이터를 가져올 수 없습니다 ({start}~{end})")
