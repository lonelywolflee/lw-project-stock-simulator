# 가격 데이터 증분 캐시 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 가격 데이터의 일자별 커버리지를 추적하여, 이미 fetch한 날짜는 건너뛰고 미캐시 범위만 네트워크에서 가져오는 증분 캐시 시스템을 구축한다.

**Architecture:** `PriceFetchCoverage` 모델로 (code, date) 단위의 fetch 완료 여부를 추적한다. services 레이어에서 커버리지를 확인하고 미커버 구간만 네트워크 fetch → 저장 → 커버리지 기록하는 오케스트레이션을 담당한다. core 레이어는 최소 변경 (빈 결과 허용하는 raw fetch 함수 추가).

**Tech Stack:** Django ORM, pytest, pytest-django, pytest-mock

---

## Task 1: PriceFetchCoverage 모델 추가

**Files:**
- Modify: `backend/apps/market_data/models.py:34` (끝에 추가)

**Step 1: 모델 코드 작성**

`backend/apps/market_data/models.py` 끝에 추가:

```python
class PriceFetchCoverage(models.Model):
    """가격 데이터 fetch 커버리지 — 일자별 fetch 완료 여부를 추적한다."""

    code = models.CharField(max_length=20)
    date = models.DateField()
    has_data = models.BooleanField(default=True)

    class Meta:
        db_table = "market_data_price_fetch_coverage"
        constraints = [
            models.UniqueConstraint(fields=["code", "date"], name="unique_price_coverage"),
        ]

    def __str__(self):
        status = "data" if self.has_data else "no-data"
        return f"{self.code} {self.date} ({status})"
```

**Step 2: 마이그레이션 생성 및 적용**

Run: `cd backend && uv run python manage.py makemigrations market_data`
Run: `cd backend && uv run python manage.py migrate`

**Step 3: 커밋**

```bash
git add backend/apps/market_data/models.py backend/apps/market_data/migrations/
git commit -m "feat: PriceFetchCoverage 모델 추가"
```

---

## Task 2: core/fetcher.py — fetch_price_data_raw 추가

**Files:**
- Modify: `backend/core/data/fetcher.py:86` (fetch_price_data 다음에 추가)
- Test: `backend/tests/test_fetcher.py` (신규)

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher.py` 생성:

```python
"""core/data/fetcher.py 순수 함수 단위 테스트."""

import pandas as pd


class TestFetchPriceDataRaw:
    def test_returns_dataframe_on_success(self, mocker):
        """네트워크 성공 시 DataFrame을 반환한다."""
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch("core.data.fetcher._retry", return_value=mock_df)

        from core.data.fetcher import fetch_price_data_raw

        df = fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")
        assert len(df) == 2
        assert "Close" in df.columns

    def test_returns_empty_dataframe_on_none(self, mocker):
        """네트워크가 None을 반환하면 빈 DataFrame을 반환한다."""
        mocker.patch("core.data.fetcher._retry", return_value=None)

        from core.data.fetcher import fetch_price_data_raw

        df = fetch_price_data_raw("005930", "2024-01-06", "2024-01-07")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_returns_empty_dataframe_on_empty_result(self, mocker):
        """네트워크가 빈 DataFrame을 반환하면 빈 DataFrame을 반환한다."""
        mocker.patch("core.data.fetcher._retry", return_value=pd.DataFrame())

        from core.data.fetcher import fetch_price_data_raw

        df = fetch_price_data_raw("005930", "2024-01-06", "2024-01-07")
        assert df.empty

    def test_propagates_network_error(self, mocker):
        """네트워크 오류는 그대로 전파한다."""
        mocker.patch("core.data.fetcher._retry", side_effect=Exception("network error"))

        from core.data.fetcher import fetch_price_data_raw
        import pytest

        with pytest.raises(Exception, match="network error"):
            fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_fetcher.py -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_price_data_raw'`

**Step 3: 구현**

`backend/core/data/fetcher.py`의 `fetch_price_data` 함수 바로 뒤 (L86 이후)에 추가:

```python
def fetch_price_data_raw(code: str, start: str, end: str) -> pd.DataFrame:
    """네트워크에서 가격 데이터를 fetch한다. 빈 결과도 허용한다.

    증분 캐시의 sub-range fetch 시 사용. ValueError를 발생시키지 않는다.
    """
    df = _retry(fdr.DataReader, code, start, end)
    if df is not None and not df.empty:
        return df
    return pd.DataFrame()
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher.py -v`
Expected: PASS (4개 모두)

**Step 5: 커밋**

```bash
git add backend/core/data/fetcher.py backend/tests/test_fetcher.py
git commit -m "feat: fetch_price_data_raw 추가 — 빈 결과 허용하는 네트워크 전용 fetch"
```

---

## Task 3: _find_uncovered_ranges 구현

**Files:**
- Modify: `backend/apps/market_data/services.py`
- Test: `backend/tests/test_fetcher_db.py` (기존 파일에 추가)

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher_db.py` 끝에 추가:

```python
from apps.market_data.models import PriceFetchCoverage
from apps.market_data.services import _find_uncovered_ranges


@pytest.mark.django_db
class TestFindUncoveredRanges:
    def test_returns_full_range_when_no_coverage(self):
        """커버리지가 없으면 전체 범위를 반환한다."""
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-04")
        assert result == [("2024-01-02", "2024-01-04")]

    def test_returns_empty_when_fully_covered(self):
        """전체가 커버되면 빈 리스트를 반환한다."""
        for day in range(2, 5):
            PriceFetchCoverage.objects.create(
                code="005930", date=datetime.date(2024, 1, day), has_data=True,
            )
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-04")
        assert result == []

    def test_returns_tail_range_when_partially_covered(self):
        """앞부분만 커버되면 뒷부분만 반환한다."""
        for day in range(2, 5):
            PriceFetchCoverage.objects.create(
                code="005930", date=datetime.date(2024, 1, day), has_data=True,
            )
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-06")
        assert result == [("2024-01-05", "2024-01-06")]

    def test_returns_multiple_uncovered_ranges(self):
        """비연속적인 다중 미커버 구간을 반환한다."""
        # 01-02, 01-03 커버 / 01-04 미커버 / 01-05 커버 / 01-06~07 미커버
        PriceFetchCoverage.objects.create(code="005930", date=datetime.date(2024, 1, 2), has_data=True)
        PriceFetchCoverage.objects.create(code="005930", date=datetime.date(2024, 1, 3), has_data=True)
        PriceFetchCoverage.objects.create(code="005930", date=datetime.date(2024, 1, 5), has_data=True)

        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-07")
        assert result == [("2024-01-04", "2024-01-04"), ("2024-01-06", "2024-01-07")]

    def test_ignores_other_codes(self):
        """다른 종목의 커버리지는 무시한다."""
        PriceFetchCoverage.objects.create(code="000660", date=datetime.date(2024, 1, 2), has_data=True)
        result = _find_uncovered_ranges("005930", "2024-01-02", "2024-01-02")
        assert result == [("2024-01-02", "2024-01-02")]
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestFindUncoveredRanges -v`
Expected: FAIL — `ImportError: cannot import name '_find_uncovered_ranges'`

**Step 3: 구현**

`backend/apps/market_data/services.py`에서:

1. import 추가 (`PriceFetchCoverage`를 models import에 추가):

```python
from .models import BatchMeta, PriceFetchCoverage, StockDailyPrice, StockListing
```

2. `_load_price_from_db` 위 (`# ── 가격 데이터 DB 콜백 ──` 섹션 내)에 추가:

```python
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
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestFindUncoveredRanges -v`
Expected: PASS (5개 모두)

**Step 5: 커밋**

```bash
git add backend/apps/market_data/services.py backend/tests/test_fetcher_db.py
git commit -m "feat: _find_uncovered_ranges 구현 — 미캐시 날짜 구간 탐지"
```

---

## Task 4: _save_coverage 구현

**Files:**
- Modify: `backend/apps/market_data/services.py`
- Test: `backend/tests/test_fetcher_db.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher_db.py` 끝에 추가:

```python
from apps.market_data.services import _save_coverage


@pytest.mark.django_db
class TestSaveCoverage:
    def test_saves_coverage_for_all_dates(self):
        """fetch 범위의 모든 날짜에 커버리지를 저장한다."""
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)

        _save_coverage("005930", "2024-01-02", "2024-01-04", df)

        coverages = list(
            PriceFetchCoverage.objects.filter(code="005930")
            .order_by("date").values_list("date", "has_data")
        )
        assert len(coverages) == 3
        assert coverages[0] == (datetime.date(2024, 1, 2), True)
        assert coverages[1] == (datetime.date(2024, 1, 3), False)  # 비거래일
        assert coverages[2] == (datetime.date(2024, 1, 4), True)

    def test_saves_all_no_data_for_empty_df(self):
        """빈 DataFrame이면 모든 날짜를 비거래일로 기록한다."""
        _save_coverage("005930", "2024-01-06", "2024-01-07", pd.DataFrame())

        coverages = list(
            PriceFetchCoverage.objects.filter(code="005930")
            .order_by("date").values_list("has_data", flat=True)
        )
        assert coverages == [False, False]

    def test_ignores_conflicts_on_duplicate(self):
        """중복 저장 시 충돌을 무시한다."""
        PriceFetchCoverage.objects.create(
            code="005930", date=datetime.date(2024, 1, 2), has_data=True,
        )
        _save_coverage("005930", "2024-01-02", "2024-01-02", pd.DataFrame())

        assert PriceFetchCoverage.objects.filter(code="005930").count() == 1
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestSaveCoverage -v`
Expected: FAIL — `ImportError: cannot import name '_save_coverage'`

**Step 3: 구현**

`backend/apps/market_data/services.py`의 `_find_uncovered_ranges` 바로 뒤에 추가:

```python
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
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestSaveCoverage -v`
Expected: PASS (3개 모두)

**Step 5: 커밋**

```bash
git add backend/apps/market_data/services.py backend/tests/test_fetcher_db.py
git commit -m "feat: _save_coverage 구현 — 일자별 fetch 커버리지 기록"
```

---

## Task 5: _load_price_from_db 수정 + fetch_price_data 증분 로직

**Files:**
- Modify: `backend/apps/market_data/services.py`
- Modify: `backend/tests/test_fetcher_db.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher_db.py`에 기존 `TestFetchPriceDataDB`를 아래로 교체:

```python
@pytest.mark.django_db
class TestFetchPriceDataDB:
    def test_returns_db_data_when_fully_covered(self):
        """전체 커버 시 네트워크 요청 없이 DB에서 반환한다."""
        for day, close in [(2, 103), (3, 106)]:
            StockDailyPrice.objects.create(
                code="005930", date=datetime.date(2024, 1, day),
                open=100, high=105, low=99, close=close, volume=1000,
            )
            PriceFetchCoverage.objects.create(
                code="005930", date=datetime.date(2024, 1, day), has_data=True,
            )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert df.iloc[0]["Close"] == 103

    def test_fetches_only_uncovered_range(self, mocker):
        """캐시된 부분은 건너뛰고 미캐시 구간만 네트워크 fetch한다."""
        # 01-02 캐시됨
        StockDailyPrice.objects.create(
            code="005930", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        PriceFetchCoverage.objects.create(
            code="005930", date=datetime.date(2024, 1, 2), has_data=True,
        )

        # 01-03~04 미캐시 → 네트워크 fetch
        dates = pd.date_range("2024-01-03", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [103, 105], "High": [107, 109],
            "Low": [102, 104], "Close": [106, 108],
            "Volume": [1200, 1100],
        }, index=dates)
        mock_raw = mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-04")

        assert len(df) == 3
        assert df.iloc[0]["Close"] == 103  # DB
        assert df.iloc[1]["Close"] == 106  # 네트워크
        # fetch_price_data_raw는 미캐시 범위만 호출됨
        mock_raw.assert_called_once()
        call_args = mock_raw.call_args
        assert call_args[0][0] == "005930"  # code

    def test_handles_non_trading_days(self, mocker):
        """비거래일이 포함된 범위를 정상 처리한다."""
        # 01-02(화), 01-03(수) 데이터 존재, 01-04(목) 비거래일(예시)
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-04")

        assert len(df) == 2  # 비거래일 01-04 제외
        # 커버리지 확인: 3일 모두 커버됨
        assert PriceFetchCoverage.objects.filter(code="005930").count() == 3
        assert PriceFetchCoverage.objects.filter(code="005930", has_data=False).count() == 1

    def test_second_call_uses_cache(self, mocker):
        """두 번째 동일 호출은 네트워크 요청 없이 캐시에서 반환한다."""
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mock_raw = mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        # 첫 번째 호출: 네트워크 fetch
        df1 = fetch_price_data("005930", "2024-01-02", "2024-01-03")
        assert mock_raw.call_count == 1

        # 두 번째 호출: 캐시 사용
        df2 = fetch_price_data("005930", "2024-01-02", "2024-01-03")
        assert mock_raw.call_count == 1  # 추가 호출 없음
        assert len(df2) == 2

    def test_fetches_from_network_and_saves(self, mocker):
        """DB에 없으면 네트워크 fetch 후 DB에 저장한다."""
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        df = fetch_price_data("005930", "2024-01-02", "2024-01-03")

        assert len(df) == 2
        assert StockDailyPrice.objects.filter(code="005930").count() == 2
        assert PriceFetchCoverage.objects.filter(code="005930").count() == 2

    def test_raises_on_network_failure(self, mocker):
        """DB에 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            side_effect=Exception("fail"),
        )

        with pytest.raises(Exception):
            fetch_price_data("005930", "2024-01-02", "2024-01-03")

        # 실패 시 커버리지 저장하지 않음
        assert PriceFetchCoverage.objects.count() == 0
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestFetchPriceDataDB -v`
Expected: FAIL

**Step 3: 구현**

`backend/apps/market_data/services.py` 수정:

1. import에 `fetch_price_data_raw` 추가:

```python
from core.data.fetcher import (
    fetch_all_prices as _core_fetch_all_prices,
    fetch_kospi_index as _core_fetch_kospi_index,
    fetch_price_data as _core_fetch_price_data,
    fetch_price_data_raw as _core_fetch_price_data_raw,
    fetch_stock_listing as _core_fetch_stock_listing,
)
```

2. `_load_price_from_db` 수정 (last_date 체크 제거):

```python
def _load_price_from_db(code: str, start: str, end: str) -> pd.DataFrame | None:
    """DB에서 가격 데이터를 로드한다."""
    records = list(
        StockDailyPrice.objects.filter(
            code=code, date__gte=start, date__lte=end,
        ).order_by("date").values("date", "open", "high", "low", "close", "volume")
    )
    if not records:
        return None

    df = pd.DataFrame(records)
    df.index = pd.to_datetime(df.pop("date"))
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df
```

3. `fetch_price_data` 교체:

```python
def fetch_price_data(code: str, start: str, end: str) -> pd.DataFrame:
    """개별 종목의 일별 가격 데이터를 반환한다 (증분 캐시)."""
    uncovered = _find_uncovered_ranges(code, start, end)

    for r_start, r_end in uncovered:
        df = _core_fetch_price_data_raw(code, r_start, r_end)
        if df is not None and not df.empty:
            _save_price_to_db(code, df, False)
        _save_coverage(code, r_start, r_end, df)

    df = _load_price_from_db(code, start, end)
    if df is not None and not df.empty:
        return df
    raise ValueError(f"{code} 가격 데이터를 가져올 수 없습니다 ({start}~{end})")
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestFetchPriceDataDB -v`
Expected: PASS (6개 모두)

**Step 5: 커밋**

```bash
git add backend/apps/market_data/services.py backend/tests/test_fetcher_db.py
git commit -m "feat: fetch_price_data 증분 캐시 적용 — 미캐시 범위만 네트워크 fetch"
```

---

## Task 6: fetch_kospi_index 증분 로직 적용

**Files:**
- Modify: `backend/apps/market_data/services.py`
- Modify: `backend/tests/test_fetcher_db.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher_db.py`에서 기존 `TestFetchKospiIndexDB`를 교체:

```python
@pytest.mark.django_db
class TestFetchKospiIndexDB:
    def test_returns_db_data_when_fully_covered(self):
        """전체 커버 시 DB에서 반환한다."""
        StockDailyPrice.objects.create(
            code="KS11", date=datetime.date(2024, 1, 2),
            open=2500, high=2520, low=2490, close=2510, volume=0, is_index=True,
        )
        PriceFetchCoverage.objects.create(
            code="KS11", date=datetime.date(2024, 1, 2), has_data=True,
        )

        df = fetch_kospi_index("2024-01-02", "2024-01-02")

        assert len(df) == 1
        assert df.iloc[0]["Close"] == 2510

    def test_second_call_uses_cache(self, mocker):
        """두 번째 동일 호출은 캐시에서 반환한다."""
        dates = pd.to_datetime(["2024-01-02"])
        mock_df = pd.DataFrame({
            "Open": [2500], "High": [2520],
            "Low": [2490], "Close": [2510],
            "Volume": [0],
        }, index=dates)
        mock_raw = mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=mock_df,
        )

        fetch_kospi_index("2024-01-02", "2024-01-02")
        assert mock_raw.call_count == 1

        fetch_kospi_index("2024-01-02", "2024-01-02")
        assert mock_raw.call_count == 1  # 추가 호출 없음
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestFetchKospiIndexDB -v`
Expected: FAIL

**Step 3: 구현**

`backend/apps/market_data/services.py`에서 `fetch_kospi_index` 교체:

```python
def fetch_kospi_index(start: str, end: str) -> pd.DataFrame:
    """KOSPI 지수(KS11) 데이터를 반환한다 (증분 캐시)."""
    uncovered = _find_uncovered_ranges("KS11", start, end)

    for r_start, r_end in uncovered:
        df = _core_fetch_price_data_raw("KS11", r_start, r_end)
        if df is not None and not df.empty:
            _save_price_to_db("KS11", df, True)
        _save_coverage("KS11", r_start, r_end, df)

    df = _load_price_from_db("KS11", start, end)
    if df is not None and not df.empty:
        return df
    raise ValueError(f"KOSPI 지수 데이터를 가져올 수 없습니다 ({start}~{end})")
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py::TestFetchKospiIndexDB -v`
Expected: PASS (2개 모두)

**Step 5: 커밋**

```bash
git add backend/apps/market_data/services.py backend/tests/test_fetcher_db.py
git commit -m "feat: fetch_kospi_index 증분 캐시 적용"
```

---

## Task 7: fetch_all_prices 및 기존 테스트 수정

**Files:**
- Modify: `backend/apps/market_data/services.py`
- Modify: `backend/tests/test_fetcher_db.py`

**Step 1: fetch_all_prices 수정**

`backend/apps/market_data/services.py`에서 `fetch_all_prices` 교체.

현재 `fetch_all_prices`는 core의 `_core_fetch_all_prices`에 DB 콜백을 주입하여 위임하고 있다. 그런데 core의 `fetch_all_prices`는 내부적으로 core의 `fetch_price_data`를 호출하므로, 증분 캐시 로직이 적용되지 않는다. services의 `fetch_price_data`를 호출하도록 변경해야 한다:

```python
def fetch_all_prices(
    codes: list[str], start: str, end: str,
    progress_callback=None,
) -> dict[str, pd.DataFrame]:
    """여러 종목의 가격 데이터를 딕셔너리로 반환한다 (증분 캐시)."""
    import logging

    logger = logging.getLogger(__name__)
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
```

**Step 2: 기존 테스트 수정**

`backend/tests/test_fetcher_db.py`에서 `TestFetchAllPricesDB` 교체:

```python
@pytest.mark.django_db
class TestFetchAllPricesDB:
    def test_skips_failed_stock_and_continues(self, mocker):
        """한 종목 실패 시 건너뛰고 나머지 진행."""
        StockDailyPrice.objects.create(
            code="A", date=datetime.date(2024, 1, 2),
            open=100, high=105, low=99, close=103, volume=1000,
        )
        PriceFetchCoverage.objects.create(
            code="A", date=datetime.date(2024, 1, 2), has_data=True,
        )
        # B는 DB에도 없고 네트워크도 실패
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            side_effect=Exception("fail"),
        )

        result = fetch_all_prices(["A", "B"], "2024-01-02", "2024-01-02")

        assert "A" in result
        assert "B" not in result
```

`TestIntegrationFlow` 교체:

```python
@pytest.mark.django_db
class TestIntegrationFlow:
    def test_listing_then_price_flow(self, mocker):
        """종목 목록 → 가격 조회 전체 흐름."""
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
        mocker.patch("core.data.fetcher._retry", side_effect=[listing_df])
        mocker.patch(
            "apps.market_data.services._core_fetch_price_data_raw",
            return_value=price_df,
        )

        listing = fetch_stock_listing("KOSPI")
        assert len(listing) == 1

        prices = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices) == 3

        # 두 번째 호출은 DB에서 가져옴
        prices2 = fetch_price_data("005930", "2024-01-02", "2024-01-04")
        assert len(prices2) == 3
```

**Step 3: 전체 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher_db.py -v`
Expected: PASS (모든 테스트)

Run: `cd backend && uv run pytest tests/ -v`
Expected: PASS (전체 테스트 스위트)

**Step 4: 커밋**

```bash
git add backend/apps/market_data/services.py backend/tests/test_fetcher_db.py
git commit -m "feat: fetch_all_prices 증분 캐시 적용 + 기존 테스트 수정"
```

---

## Task 8: 불필요한 core import 정리

**Files:**
- Modify: `backend/apps/market_data/services.py`

**Step 1: 사용하지 않는 import 제거**

services.py에서 더 이상 사용하지 않는 core import를 정리한다:

```python
from core.data.fetcher import (
    fetch_price_data_raw as _core_fetch_price_data_raw,
    fetch_stock_listing as _core_fetch_stock_listing,
)
```

`_core_fetch_all_prices`, `_core_fetch_kospi_index`, `_core_fetch_price_data`는 더 이상 사용하지 않으므로 제거.

**Step 2: 전체 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/ -v`
Expected: PASS

**Step 3: 커밋**

```bash
git add backend/apps/market_data/services.py
git commit -m "refactor: 사용하지 않는 core fetcher import 제거"
```
