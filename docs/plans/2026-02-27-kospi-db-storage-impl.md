# KOSPI DB 저장 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KOSPI 종목 정보와 일별 가격 데이터를 DB에 저장하여 파일 캐시를 대체한다.

**Architecture:** Django ORM으로 3개 모델(BatchMeta, StockListing, StockDailyPrice) 생성. `fetcher.py`가 DB 우선 조회 후 미스 시 FinanceDataReader fetch → DB 저장. 파일 캐시(cache.py) 삭제.

**Tech Stack:** Django 5.1 ORM, SQLite, FinanceDataReader, pandas

---

### Task 1: Django 모델 생성

**Files:**
- Create: `backend/apps/market_data/models.py`

**Step 1: 모델 파일 생성**

```python
"""시장 데이터 Django 모델."""

from django.db import models


class BatchMeta(models.Model):
    """배치 작업 메타 정보 — 마지막 fetch 일자를 추적한다."""

    job_name = models.CharField(max_length=100, unique=True)
    last_fetched_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_data_batch_meta"

    def __str__(self):
        return f"{self.job_name} ({self.last_fetched_date})"


class StockListing(models.Model):
    """KOSPI 상장 종목 정보."""

    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    market_cap = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "market_data_stock_listing"

    def __str__(self):
        return f"{self.code} {self.name}"


class StockDailyPrice(models.Model):
    """종목 및 지수의 일별 OHLCV 데이터."""

    code = models.CharField(max_length=20, db_index=True)
    date = models.DateField(db_index=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.BigIntegerField()
    is_index = models.BooleanField(default=False)

    class Meta:
        db_table = "market_data_stock_daily_price"
        unique_together = [("code", "date")]
        indexes = [
            models.Index(fields=["code", "date"]),
        ]

    def __str__(self):
        return f"{self.code} {self.date} C={self.close}"
```

**Step 2: 마이그레이션 생성 및 적용**

Run: `cd backend && python manage.py makemigrations market_data && python manage.py migrate`

**Step 3: 커밋**

```bash
git add backend/apps/market_data/models.py backend/apps/market_data/migrations/
git commit -m "feat: 시장 데이터 Django 모델 추가 (BatchMeta, StockListing, StockDailyPrice)"
```

---

### Task 2: Admin 등록

**Files:**
- Create: `backend/apps/market_data/admin.py`

**Step 1: admin.py 생성**

```python
"""시장 데이터 Admin."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import BatchMeta, StockDailyPrice, StockListing


@admin.register(BatchMeta)
class BatchMetaAdmin(ModelAdmin):
    list_display = ("job_name", "last_fetched_date", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(StockListing)
class StockListingAdmin(ModelAdmin):
    list_display = ("code", "name", "market_cap")
    search_fields = ("code", "name")


@admin.register(StockDailyPrice)
class StockDailyPriceAdmin(ModelAdmin):
    list_display = ("code", "date", "close", "volume", "is_index")
    list_filter = ("is_index",)
    search_fields = ("code",)
```

**Step 2: 커밋**

```bash
git add backend/apps/market_data/admin.py
git commit -m "feat: 시장 데이터 모델 Admin 등록"
```

---

### Task 3: fetcher.py DB 연동 — 종목 목록

**Files:**
- Modify: `backend/core/data/fetcher.py`

**Step 1: 테스트 작성**

Create: `backend/tests/test_fetcher_db.py`

```python
"""fetcher DB 연동 테스트."""

import datetime

import pandas as pd
import pytest

from apps.market_data.models import BatchMeta, StockListing
from core.data.fetcher import fetch_stock_listing


@pytest.mark.django_db
class TestFetchStockListingDB:
    def test_returns_db_data_when_batch_is_today(self):
        """오늘 배치 완료 시 DB 데이터를 반환한다."""
        StockListing.objects.create(code="005930", name="삼성전자", market_cap=500_000_000_000)
        StockListing.objects.create(code="000660", name="SK하이닉스", market_cap=100_000_000_000)
        BatchMeta.objects.create(job_name="kospi_listing", last_fetched_date=datetime.date.today())

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 2
        assert "Code" in df.columns
        assert "Name" in df.columns
        assert "Marcap" in df.columns

    def test_fetches_from_network_when_no_batch(self, mocker):
        """배치 기록이 없으면 네트워크에서 fetch하고 DB에 저장한다."""
        mock_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Marcap": [500_000_000_000],
        })
        mocker.patch("core.data.fetcher._retry", return_value=mock_df)

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert StockListing.objects.count() == 1
        assert BatchMeta.objects.filter(job_name="kospi_listing").exists()

    def test_uses_db_fallback_on_network_error(self, mocker):
        """네트워크 실패 시 기존 DB 데이터를 반환한다."""
        StockListing.objects.create(code="005930", name="삼성전자", market_cap=500_000_000_000)
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("network error"))

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert df.iloc[0]["Code"] == "005930"

    def test_raises_when_no_db_and_network_fails(self, mocker):
        """DB도 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("network error"))

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend && python -m pytest tests/test_fetcher_db.py -v`
Expected: FAIL (fetch_stock_listing이 아직 DB를 사용하지 않음)

**Step 3: fetch_stock_listing 구현 변경**

`backend/core/data/fetcher.py`의 `fetch_stock_listing` 함수를 아래로 교체:

```python
def fetch_stock_listing(market: str = "KOSPI") -> pd.DataFrame:
    """상장 종목 목록을 반환한다.

    1. BatchMeta에서 오늘 fetch 했는지 확인
    2. 오늘 이미 fetch → DB에서 조회
    3. fetch 안 함 → FinanceDataReader 호출 → DB 저장 → BatchMeta 갱신
    4. 네트워크 실패 → DB 기존 데이터 사용 (없으면 예외)
    """
    import datetime
    from apps.market_data.models import BatchMeta, StockListing

    today = datetime.date.today()
    batch = BatchMeta.objects.filter(job_name=f"{market.lower()}_listing").first()

    if batch and batch.last_fetched_date == today:
        return _listing_from_db()

    # 네트워크 fetch 시도
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
```

**Step 4: 테스트 실행 — 통과 확인**

Run: `cd backend && python -m pytest tests/test_fetcher_db.py::TestFetchStockListingDB -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add backend/core/data/fetcher.py backend/tests/test_fetcher_db.py
git commit -m "feat: fetch_stock_listing DB 연동 (배치 메타 + fallback)"
```

---

### Task 4: fetcher.py DB 연동 — 가격 데이터

**Files:**
- Modify: `backend/core/data/fetcher.py`
- Modify: `backend/tests/test_fetcher_db.py`

**Step 1: 테스트 추가**

`backend/tests/test_fetcher_db.py`에 추가:

```python
from apps.market_data.models import StockDailyPrice
from core.data.fetcher import fetch_price_data, fetch_kospi_index


@pytest.mark.django_db
class TestFetchPriceDataDB:
    def test_returns_db_data_when_exists(self):
        """DB에 데이터가 있으면 DB에서 반환한다."""
        StockDailyPrice.objects.create(
            code="005930", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        StockDailyPrice.objects.create(
            code="005930", date=datetime.date(2024, 1, 3),
            open=103, high=107, low=102, close=106, volume=1200,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert "Close" in df.columns
        assert df.iloc[0]["Close"] == 103

    def test_fetches_from_network_and_saves(self, mocker):
        """DB에 없으면 네트워크 fetch 후 DB에 저장한다."""
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch("core.data.fetcher._retry", return_value=mock_df)

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert StockDailyPrice.objects.filter(code="005930").count() == 2

    def test_raises_on_network_failure(self, mocker):
        """DB에 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("fail"))

        with pytest.raises(Exception):
            fetch_price_data("005930", "2024-01-02", "2024-01-03")


@pytest.mark.django_db
class TestFetchKospiIndexDB:
    def test_returns_db_data_when_exists(self):
        """DB에 KS11 데이터가 있으면 반환한다."""
        StockDailyPrice.objects.create(
            code="KS11", date=datetime.date(2024, 1, 2),
            open=2500, high=2520, low=2490, close=2510, volume=0, is_index=True,
        )

        df = fetch_kospi_index("2024-01-02", "2024-01-02")

        assert len(df) == 1
        assert df.iloc[0]["Close"] == 2510
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend && python -m pytest tests/test_fetcher_db.py::TestFetchPriceDataDB -v`
Expected: FAIL

**Step 3: fetch_price_data, fetch_kospi_index 구현 변경**

`backend/core/data/fetcher.py`에서 cache import 제거하고 아래로 교체:

```python
def fetch_price_data(code: str, start: str, end: str, username: str = "") -> pd.DataFrame:
    """개별 종목의 일별 가격 데이터를 반환한다. DB를 우선 확인한다."""
    df = _price_from_db(code, start, end)
    if df is not None and not df.empty:
        return df

    df = _retry(fdr.DataReader, code, start, end)
    if df is not None and not df.empty:
        _save_price_to_db(code, df, is_index=False)
        return df
    raise ValueError(f"{code} 가격 데이터를 가져올 수 없습니다 ({start}~{end})")


def fetch_kospi_index(start: str, end: str, username: str = "") -> pd.DataFrame:
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
```

**Step 4: cache import 제거**

`fetcher.py` 상단의 `from core.data.cache import load_from_cache, save_to_cache` 삭제

**Step 5: 테스트 실행 — 통과 확인**

Run: `cd backend && python -m pytest tests/test_fetcher_db.py -v`
Expected: PASS

**Step 6: 커밋**

```bash
git add backend/core/data/fetcher.py backend/tests/test_fetcher_db.py
git commit -m "feat: fetch_price_data/fetch_kospi_index DB 연동"
```

---

### Task 5: fetch_all_prices 에러 핸들링 강화

**Files:**
- Modify: `backend/core/data/fetcher.py`
- Modify: `backend/tests/test_fetcher_db.py`

**Step 1: 테스트 추가**

```python
from core.data.fetcher import fetch_all_prices


@pytest.mark.django_db
class TestFetchAllPricesDB:
    def test_skips_failed_stock_and_continues(self, mocker):
        """한 종목 실패 시 건너뛰고 나머지 진행."""
        StockDailyPrice.objects.create(
            code="A", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        # B는 DB에도 없고 네트워크도 실패
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("fail"))

        result = fetch_all_prices(["A", "B"], "2024-01-02", "2024-01-02")

        assert "A" in result
        assert "B" not in result
```

**Step 2: fetch_all_prices 수정**

`fetch_all_prices`에서 `fetch_price_data`가 예외를 던질 때 기존처럼 warning 후 건너뛰도록 유지:

```python
def fetch_all_prices(
    codes: list[str], start: str, end: str,
    progress_callback=None, username: str = "",
) -> dict[str, pd.DataFrame]:
    """여러 종목의 가격 데이터를 딕셔너리로 반환한다."""
    result: dict[str, pd.DataFrame] = {}
    for i, code in enumerate(codes):
        try:
            df = fetch_price_data(code, start, end, username=username)
            if df is not None and not df.empty:
                result[code] = df
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", code, e)
        if progress_callback:
            progress_callback(i + 1, len(codes))
    return result
```

**Step 3: 테스트 통과 확인**

Run: `cd backend && python -m pytest tests/test_fetcher_db.py -v`
Expected: PASS

**Step 4: 커밋**

```bash
git add backend/core/data/fetcher.py backend/tests/test_fetcher_db.py
git commit -m "feat: fetch_all_prices DB 연동 및 에러 핸들링"
```

---

### Task 6: cache.py 삭제 및 market_data API 수정

**Files:**
- Delete: `backend/core/data/cache.py`
- Modify: `backend/apps/market_data/api.py`

**Step 1: cache.py 삭제**

```bash
rm backend/core/data/cache.py
```

**Step 2: market_data API를 DB 기반으로 수정**

```python
"""시장 데이터 API."""

from ninja import Router

from core.data.fetcher import fetch_stock_listing

from .schemas import StockSchema

router = Router()


@router.get("/stocks/{market}", response=list[StockSchema])
def list_stocks(request, market: str, limit: int = 100):
    """상장 종목 목록 조회."""
    df = fetch_stock_listing(market.upper())
    if df is None or df.empty:
        return []

    records = []
    for _, row in df.head(limit).iterrows():
        records.append({
            "code": row.get("Code", ""),
            "name": row.get("Name", ""),
            "market_cap": int(row.get("Marcap", 0)) if row.get("Marcap") else None,
        })
    return records
```

**Step 3: 기존 테스트 전체 실행**

Run: `cd backend && python -m pytest -v`
Expected: 모든 테스트 PASS (기존 backtest 테스트는 fetcher를 직접 호출하지 않으므로 영향 없음)

**Step 4: 커밋**

```bash
git add -A
git commit -m "refactor: 파일 캐시 삭제, market_data API 간소화"
```

---

### Task 7: 전체 통합 테스트

**Files:**
- Modify: `backend/tests/test_fetcher_db.py`

**Step 1: 통합 시나리오 테스트 추가**

```python
@pytest.mark.django_db
class TestIntegrationFlow:
    def test_listing_then_price_flow(self, mocker):
        """종목 목록 → 가격 조회 전체 흐름."""
        # 1. listing fetch mock
        listing_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Marcap": [500_000_000_000],
        })
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        price_df = pd.DataFrame({
            "Open": [70000, 71000, 72000],
            "High": [71000, 72000, 73000],
            "Low": [69000, 70000, 71000],
            "Close": [70500, 71500, 72500],
            "Volume": [10000, 12000, 11000],
        }, index=dates)
        mocker.patch("core.data.fetcher._retry", side_effect=[listing_df, price_df])

        # 2. 종목 목록 fetch (네트워크 → DB 저장)
        listing = fetch_stock_listing("KOSPI")
        assert len(listing) == 1

        # 3. 가격 fetch (네트워크 → DB 저장)
        prices = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices) == 3

        # 4. 두 번째 호출은 DB에서 가져옴 (mock이 소진되어도 OK)
        prices2 = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices2) == 3
```

**Step 2: 전체 테스트 실행**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

**Step 3: 커밋**

```bash
git add backend/tests/test_fetcher_db.py
git commit -m "test: DB 연동 통합 테스트 추가"
```
