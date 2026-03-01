"""시장 데이터 서비스 — DB 접근 로직 + core fetcher 조합.

core/data/fetcher.py의 순수 함수에 DB 콜백을 주입하여
종목 목록/가격 데이터의 DB 우선 조회 → 네트워크 fetch → DB 저장을 오케스트레이션한다.
"""

import datetime

import pandas as pd

from core.data.fetcher import (
    fetch_all_prices as _core_fetch_all_prices,
    fetch_kospi_index as _core_fetch_kospi_index,
    fetch_price_data as _core_fetch_price_data,
    fetch_stock_listing as _core_fetch_stock_listing,
)

from .models import BatchMeta, PriceFetchCoverage, StockDailyPrice, StockListing


# ── 종목 목록 DB 콜백 ──────────────────────────────────────────


def _is_listing_batch_done(market: str) -> bool:
    batch = BatchMeta.objects.filter(job_name=f"{market.lower()}_listing").first()
    return batch is not None and batch.last_fetched_date == datetime.date.today()


def _load_listing_from_db() -> pd.DataFrame | None:
    records = list(StockListing.objects.all().values("code", "name", "market_cap"))
    if not records:
        return None
    return pd.DataFrame({
        "Code": [r["code"] for r in records],
        "Name": [r["name"] for r in records],
        "Marcap": [r["market_cap"] for r in records],
    })


def _save_listing_to_db(df: pd.DataFrame) -> None:
    code_col = "Code" if "Code" in df.columns else "Symbol"
    cap_col = "Marcap" if "Marcap" in df.columns else "MarketCap"

    objects = []
    for _, row in df.iterrows():
        code = row.get(code_col, "")
        if not code:
            continue
        objects.append(StockListing(
            code=code,
            name=row.get("Name", ""),
            market_cap=int(row.get(cap_col, 0)) if row.get(cap_col) else None,
        ))
    StockListing.objects.bulk_create(
        objects,
        update_conflicts=True,
        unique_fields=["code"],
        update_fields=["name", "market_cap"],
    )


def _mark_listing_batch_done(market: str) -> None:
    BatchMeta.objects.update_or_create(
        job_name=f"{market.lower()}_listing",
        defaults={"last_fetched_date": datetime.date.today()},
    )


# ── 가격 데이터 DB 콜백 ────────────────────────────────────────


def _find_uncovered_ranges(code: str, start: str, end: str) -> list[tuple[str, str]]:
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
            code=code, date__gte=start_date, date__lte=end_date,
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


def _save_coverage(code: str, start: str, end: str, fetched_df: pd.DataFrame) -> None:
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
            code=code, date=current, has_data=current in data_dates,
        ))
        current += datetime.timedelta(days=1)

    PriceFetchCoverage.objects.bulk_create(objects, ignore_conflicts=True)


def _load_price_from_db(code: str, start: str, end: str) -> pd.DataFrame | None:
    records = list(
        StockDailyPrice.objects.filter(
            code=code, date__gte=start, date__lte=end,
        ).order_by("date").values("date", "open", "high", "low", "close", "volume")
    )
    if not records:
        return None

    # end 날짜 근처 데이터가 없으면 불완전 → 네트워크 fetch 유도
    last_date = str(records[-1]["date"])
    if last_date < end:
        return None

    df = pd.DataFrame(records)
    df.index = pd.to_datetime(df.pop("date"))
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df


def _save_price_to_db(code: str, df: pd.DataFrame, is_index: bool = False) -> None:
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


# ── 공개 API (DB 콜백이 주입된 fetcher) ────────────────────────


def fetch_stock_listing(market: str = "KOSPI") -> pd.DataFrame:
    """상장 종목 목록을 반환한다 (DB 배치 관리 포함)."""
    return _core_fetch_stock_listing(
        market,
        is_batch_done=lambda: _is_listing_batch_done(market),
        load_listing=_load_listing_from_db,
        save_listing=_save_listing_to_db,
        mark_batch_done=lambda: _mark_listing_batch_done(market),
    )


def fetch_price_data(code: str, start: str, end: str) -> pd.DataFrame:
    """개별 종목의 일별 가격 데이터를 반환한다 (DB 우선 조회)."""
    return _core_fetch_price_data(
        code, start, end,
        load_price=_load_price_from_db,
        save_price=_save_price_to_db,
    )


def fetch_all_prices(
    codes: list[str], start: str, end: str,
    progress_callback=None,
) -> dict[str, pd.DataFrame]:
    """여러 종목의 가격 데이터를 딕셔너리로 반환한다 (DB 우선 조회)."""
    return _core_fetch_all_prices(
        codes, start, end,
        progress_callback=progress_callback,
        load_price=_load_price_from_db,
        save_price=_save_price_to_db,
    )


def fetch_kospi_index(start: str, end: str) -> pd.DataFrame:
    """KOSPI 지수(KS11) 데이터를 반환한다 (DB 우선 조회)."""
    return _core_fetch_kospi_index(
        start, end,
        load_price=_load_price_from_db,
        save_price=_save_price_to_db,
    )
