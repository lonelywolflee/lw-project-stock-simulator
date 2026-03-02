# 데이터 Provider 이중화 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** FDR 실패 시 pykrx로 자동 fallback하는 provider 이중화 시스템을 구축한다.

**Architecture:** 각 provider는 동일한 인터페이스(`stock_listing`, `price_data`)를 구현하는 순수 함수 모듈이다. fetcher.py의 `_fetch_with_fallback`이 provider 목록을 순서대로 시도하며, 각 provider는 `_retry`로 재시도 후 실패 시 다음 provider로 넘어간다.

**Tech Stack:** FinanceDataReader, pykrx, pandas, pytest

---

## Task 1: pykrx 의존성 추가

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: 의존성 추가**

`backend/pyproject.toml`의 `dependencies` 리스트에 `"pykrx"` 추가:

```toml
dependencies = [
    "django>=5.1,<6.0",
    "django-ninja>=1.3,<2.0",
    "django-cors-headers>=4.4",
    "finance-datareader",
    "pykrx",
    "pandas",
    "numpy",

    "python-dotenv>=1.0",
    "django-unfold>=0.81.0",
]
```

**Step 2: 설치**

Run: `cd backend && uv sync`

**Step 3: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "feat: pykrx 의존성 추가"
```

---

## Task 2: providers 패키지 + fdr_provider 구현

**Files:**
- Create: `backend/core/data/providers/__init__.py`
- Create: `backend/core/data/providers/fdr_provider.py`
- Create: `backend/tests/test_providers.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_providers.py` 생성:

```python
"""데이터 provider 단위 테스트."""

import pandas as pd
import pytest


class TestFdrProvider:
    def test_stock_listing_returns_standard_columns(self, mocker):
        """FDR provider가 표준 컬럼(Code, Name, Marcap)을 반환한다."""
        mock_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Marcap": [500_000_000_000],
        })
        mocker.patch("FinanceDataReader.StockListing", return_value=mock_df)

        from core.data.providers.fdr_provider import stock_listing

        df = stock_listing("KOSPI")
        assert list(df.columns) >= ["Code", "Name", "Marcap"]
        assert len(df) == 1

    def test_price_data_returns_standard_columns(self, mocker):
        """FDR provider가 표준 OHLCV 컬럼을 반환한다."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        mock_df = pd.DataFrame({
            "Open": [100, 103], "High": [105, 107],
            "Low": [99, 102], "Close": [103, 106],
            "Volume": [1000, 1200],
        }, index=dates)
        mocker.patch("FinanceDataReader.DataReader", return_value=mock_df)

        from core.data.providers.fdr_provider import price_data

        df = price_data("005930", "2024-01-02", "2024-01-03")
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert len(df) == 2

    def test_price_data_returns_empty_on_none(self, mocker):
        """FDR이 None 반환 시 빈 DataFrame을 반환한다."""
        mocker.patch("FinanceDataReader.DataReader", return_value=None)

        from core.data.providers.fdr_provider import price_data

        df = price_data("005930", "2024-01-02", "2024-01-03")
        assert df.empty
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_providers.py::TestFdrProvider -v`

**Step 3: providers 패키지 생성**

`backend/core/data/providers/__init__.py`:

```python
"""데이터 provider 인터페이스.

각 provider 모듈은 다음 함수를 구현한다:

    stock_listing(market: str) -> pd.DataFrame
        columns: ["Code", "Name", "Marcap"]

    price_data(code: str, start: str, end: str) -> pd.DataFrame
        index: DatetimeIndex
        columns: ["Open", "High", "Low", "Close", "Volume"]
"""
```

`backend/core/data/providers/fdr_provider.py`:

```python
"""FinanceDataReader 기반 데이터 provider."""

import FinanceDataReader as fdr
import pandas as pd


def stock_listing(market: str) -> pd.DataFrame:
    """상장 종목 목록을 반환한다."""
    return fdr.StockListing(market)


def price_data(code: str, start: str, end: str) -> pd.DataFrame:
    """일별 가격 데이터를 반환한다."""
    df = fdr.DataReader(code, start, end)
    if df is None or df.empty:
        return pd.DataFrame()
    return df
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_providers.py::TestFdrProvider -v`

**Step 5: 커밋**

```bash
git add backend/core/data/providers/ backend/tests/test_providers.py
git commit -m "feat: fdr_provider 구현 — FinanceDataReader 래핑"
```

---

## Task 3: pykrx_provider 구현

**Files:**
- Create: `backend/core/data/providers/pykrx_provider.py`
- Modify: `backend/tests/test_providers.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_providers.py` 끝에 추가:

```python
class TestPykrxProvider:
    def test_stock_listing_converts_to_standard_format(self, mocker):
        """pykrx provider가 한글 데이터를 표준 포맷으로 변환한다."""
        mocker.patch(
            "pykrx.stock.get_market_ticker_list",
            return_value=["005930", "000660"],
        )
        mocker.patch(
            "pykrx.stock.get_market_ticker_name",
            side_effect=["삼성전자", "SK하이닉스"],
        )
        cap_df = pd.DataFrame(
            {"시가총액": [500_000_000_000, 100_000_000_000]},
            index=["005930", "000660"],
        )
        mocker.patch("pykrx.stock.get_market_cap", return_value=cap_df)

        from core.data.providers.pykrx_provider import stock_listing

        df = stock_listing("KOSPI")
        assert list(df.columns) == ["Code", "Name", "Marcap"]
        assert len(df) == 2
        assert df.iloc[0]["Code"] == "005930"
        assert df.iloc[0]["Name"] == "삼성전자"
        assert df.iloc[0]["Marcap"] == 500_000_000_000

    def test_price_data_converts_korean_columns(self, mocker):
        """pykrx provider가 한글 컬럼을 영문으로 변환한다."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        raw_df = pd.DataFrame({
            "시가": [100, 103], "고가": [105, 107],
            "저가": [99, 102], "종가": [103, 106],
            "거래량": [1000, 1200], "거래대금": [0, 0], "등락률": [0, 0],
        }, index=dates)
        mocker.patch("pykrx.stock.get_market_ohlcv", return_value=raw_df)

        from core.data.providers.pykrx_provider import price_data

        df = price_data("005930", "2024-01-02", "2024-01-03")
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert len(df) == 2
        assert df.iloc[0]["Close"] == 103

    def test_price_data_converts_date_format(self, mocker):
        """pykrx provider가 날짜 형식을 변환한다 (2024-01-02 → 20240102)."""
        mocker.patch("pykrx.stock.get_market_ohlcv", return_value=pd.DataFrame())

        from core.data.providers.pykrx_provider import price_data

        price_data("005930", "2024-01-02", "2024-01-03")
        from pykrx.stock import get_market_ohlcv
        get_market_ohlcv.assert_called_once_with("20240102", "20240103", "005930")

    def test_price_data_returns_empty_on_empty(self, mocker):
        """빈 결과 시 빈 DataFrame을 반환한다."""
        mocker.patch("pykrx.stock.get_market_ohlcv", return_value=pd.DataFrame())

        from core.data.providers.pykrx_provider import price_data

        df = price_data("005930", "2024-01-02", "2024-01-03")
        assert df.empty
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_providers.py::TestPykrxProvider -v`

**Step 3: 구현**

`backend/core/data/providers/pykrx_provider.py`:

```python
"""pykrx 기반 데이터 provider — KRX 스크래핑 fallback."""

import datetime

import pandas as pd
from pykrx import stock


def stock_listing(market: str) -> pd.DataFrame:
    """상장 종목 목록을 반환한다."""
    today = datetime.date.today().strftime("%Y%m%d")
    tickers = stock.get_market_ticker_list(today, market)

    cap_df = stock.get_market_cap(today, market=market)

    records = []
    for ticker in tickers:
        name = stock.get_market_ticker_name(ticker)
        marcap = int(cap_df.loc[ticker, "시가총액"]) if ticker in cap_df.index else 0
        records.append({"Code": ticker, "Name": name, "Marcap": marcap})

    return pd.DataFrame(records)


def price_data(code: str, start: str, end: str) -> pd.DataFrame:
    """일별 가격 데이터를 반환한다."""
    start_fmt = start.replace("-", "")
    end_fmt = end.replace("-", "")

    df = stock.get_market_ohlcv(start_fmt, end_fmt, code)
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.rename(columns={
        "시가": "Open",
        "고가": "High",
        "저가": "Low",
        "종가": "Close",
        "거래량": "Volume",
    })
    return df[["Open", "High", "Low", "Close", "Volume"]]
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_providers.py -v`

**Step 5: 커밋**

```bash
git add backend/core/data/providers/pykrx_provider.py backend/tests/test_providers.py
git commit -m "feat: pykrx_provider 구현 — KRX 스크래핑 fallback provider"
```

---

## Task 4: fetcher.py — fallback 로직 적용

**Files:**
- Modify: `backend/core/data/fetcher.py`
- Modify: `backend/tests/test_fetcher.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher.py` 전체를 교체:

```python
"""core/data/fetcher.py 단위 테스트."""

import pandas as pd
import pytest

from core.data.fetcher import fetch_price_data_raw


def _make_price_df():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    return pd.DataFrame({
        "Open": [100, 103], "High": [105, 107],
        "Low": [99, 102], "Close": [103, 106],
        "Volume": [1000, 1200],
    }, index=dates)


class TestFetchWithFallback:
    def test_uses_primary_on_success(self, mocker):
        """primary provider 성공 시 그대로 반환한다."""
        mock_df = _make_price_df()
        mocker.patch("core.data.providers.fdr_provider.price_data", return_value=mock_df)
        fallback = mocker.patch("core.data.providers.pykrx_provider.price_data")

        df = fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")
        assert len(df) == 2
        fallback.assert_not_called()

    def test_falls_back_on_primary_failure(self, mocker):
        """primary 실패 시 fallback provider를 사용한다."""
        mock_df = _make_price_df()
        mocker.patch(
            "core.data.providers.fdr_provider.price_data",
            side_effect=Exception("FDR down"),
        )
        mocker.patch("core.data.providers.pykrx_provider.price_data", return_value=mock_df)

        df = fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")
        assert len(df) == 2

    def test_raises_when_all_providers_fail(self, mocker):
        """모든 provider 실패 시 예외를 발생시킨다."""
        mocker.patch(
            "core.data.providers.fdr_provider.price_data",
            side_effect=Exception("FDR down"),
        )
        mocker.patch(
            "core.data.providers.pykrx_provider.price_data",
            side_effect=Exception("pykrx down"),
        )

        with pytest.raises(Exception, match="pykrx down"):
            fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")


class TestFetchPriceDataRaw:
    def test_returns_dataframe_on_success(self, mocker):
        """네트워크 성공 시 DataFrame을 반환한다."""
        mock_df = _make_price_df()
        mocker.patch("core.data.providers.fdr_provider.price_data", return_value=mock_df)

        df = fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")
        assert len(df) == 2
        assert "Close" in df.columns

    def test_returns_empty_dataframe_on_empty_result(self, mocker):
        """빈 결과 시 빈 DataFrame을 반환한다."""
        mocker.patch("core.data.providers.fdr_provider.price_data", return_value=pd.DataFrame())

        df = fetch_price_data_raw("005930", "2024-01-06", "2024-01-07")
        assert df.empty

    def test_propagates_error_after_all_fallbacks(self, mocker):
        """모든 provider 실패 시 오류를 전파한다."""
        mocker.patch(
            "core.data.providers.fdr_provider.price_data",
            side_effect=Exception("fail"),
        )
        mocker.patch(
            "core.data.providers.pykrx_provider.price_data",
            side_effect=Exception("fail2"),
        )

        with pytest.raises(Exception):
            fetch_price_data_raw("005930", "2024-01-02", "2024-01-03")
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_fetcher.py -v`

**Step 3: fetcher.py 수정**

`backend/core/data/fetcher.py` 전체를 교체:

```python
"""데이터 수집 모듈 — provider 이중화 + retry/fallback.

순수 데이터 수집 로직만 담당한다. DB 접근은 콜백으로 주입받는다.
primary provider(FDR) 실패 시 fallback provider(pykrx)로 자동 전환한다.
"""

import logging
import time
from collections.abc import Callable

import pandas as pd

from core.data.providers import fdr_provider, pykrx_provider

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds

LISTING_PROVIDERS = [fdr_provider.stock_listing, pykrx_provider.stock_listing]
PRICE_PROVIDERS = [fdr_provider.price_data, pykrx_provider.price_data]


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


def _fetch_with_fallback(providers, *args, retries: int = MAX_RETRIES):
    """provider 목록을 순서대로 시도한다. 각 provider는 재시도 후 실패 시 다음으로."""
    last_error = None
    for provider in providers:
        try:
            return _retry(provider, *args, retries=retries)
        except Exception as e:
            last_error = e
            logger.warning("Provider %s 실패: %s", getattr(provider, "__module__", "?"), e)
    raise last_error


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
    2. 아니면 provider 호출 (FDR → pykrx fallback) → save_listing() → mark_batch_done()
    3. 전체 실패 → load_listing() fallback (없으면 예외)
    """
    if is_batch_done and is_batch_done():
        df = load_listing() if load_listing else None
        if df is not None and not df.empty:
            return df

    try:
        df = _fetch_with_fallback(LISTING_PROVIDERS, market)
        if save_listing:
            save_listing(df)
        if mark_batch_done:
            mark_batch_done()
        return df
    except Exception:
        logger.warning("종목 목록 fetch 실패, fallback 시도")
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

    load_price로 저장소 조회 후 미스 시 provider fetch (FDR → pykrx fallback) → save_price로 저장.
    """
    if load_price:
        df = load_price(code, start, end)
        if df is not None and not df.empty:
            return df

    df = _fetch_with_fallback(PRICE_PROVIDERS, code, start, end)
    if df is not None and not df.empty:
        if save_price:
            save_price(code, df, False)
        return df
    raise ValueError(f"{code} 가격 데이터를 가져올 수 없습니다 ({start}~{end})")


def fetch_price_data_raw(code: str, start: str, end: str) -> pd.DataFrame:
    """네트워크에서 가격 데이터를 fetch한다. 빈 결과도 허용한다.

    증분 캐시의 sub-range fetch 시 사용. ValueError를 발생시키지 않는다.
    """
    try:
        df = _fetch_with_fallback(PRICE_PROVIDERS, code, start, end)
    except Exception:
        return pd.DataFrame()
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


def fetch_kospi_index(
    start: str, end: str,
    *,
    load_price: Callable[[str, str, str], pd.DataFrame | None] | None = None,
    save_price: Callable[[str, pd.DataFrame, bool], None] | None = None,
) -> pd.DataFrame:
    """KOSPI 지수(KS11) 데이터를 반환한다."""
    if load_price:
        df = load_price("KS11", start, end)
        if df is not None and not df.empty:
            return df

    df = _fetch_with_fallback(PRICE_PROVIDERS, "KS11", start, end)
    if df is not None and not df.empty:
        if save_price:
            save_price("KS11", df, True)
        return df
    raise ValueError(f"KOSPI 지수 데이터를 가져올 수 없습니다 ({start}~{end})")
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher.py -v`

**Step 5: 커밋**

```bash
git add backend/core/data/fetcher.py backend/tests/test_fetcher.py
git commit -m "feat: fetcher에 provider 이중화 적용 — FDR → pykrx fallback"
```

---

## Task 5: services 테스트 mock 대상 수정

**Files:**
- Modify: `backend/tests/test_fetcher_db.py`

services 레이어 테스트 중 `core.data.fetcher._retry`를 mock하던 테스트들의 mock 대상을 provider로 변경한다.

**Step 1: mock 대상 변경**

`test_fetcher_db.py`에서 `core.data.fetcher._retry`를 mock하는 곳:
- `TestFetchStockListingDB.test_fetches_from_network_when_no_batch` (L39)
- `TestFetchStockListingDB.test_uses_db_fallback_on_network_error` (L50)
- `TestFetchStockListingDB.test_raises_when_no_db_and_network_fails` (L59)
- `TestIntegrationFlow.test_listing_then_price_flow` (L259)

변경: `mocker.patch("core.data.fetcher._retry", ...)` → `mocker.patch("core.data.fetcher._fetch_with_fallback", ...)`

`TestFetchStockListingDB` 변경:

```python
    def test_fetches_from_network_when_no_batch(self, mocker):
        """배치 기록이 없으면 네트워크에서 fetch하고 DB에 저장한다."""
        mock_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Marcap": [500_000_000_000],
        })
        mocker.patch("core.data.fetcher._fetch_with_fallback", return_value=mock_df)

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert StockListing.objects.count() == 1
        assert BatchMeta.objects.filter(job_name="kospi_listing").exists()

    def test_uses_db_fallback_on_network_error(self, mocker):
        """네트워크 실패 시 기존 DB 데이터를 반환한다."""
        StockListing.objects.create(code="005930", name="삼성전자", market_cap=500_000_000_000)
        mocker.patch("core.data.fetcher._fetch_with_fallback", side_effect=Exception("network error"))

        df = fetch_stock_listing("KOSPI")

        assert len(df) == 1
        assert df.iloc[0]["Code"] == "005930"

    def test_raises_when_no_db_and_network_fails(self, mocker):
        """DB도 없고 네트워크도 실패하면 예외 발생."""
        mocker.patch("core.data.fetcher._fetch_with_fallback", side_effect=Exception("network error"))

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")
```

`TestIntegrationFlow` 변경:

```python
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
        mocker.patch("core.data.fetcher._fetch_with_fallback", side_effect=[listing_df])
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

**Step 2: 전체 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/ -v`
Expected: 전체 PASS

**Step 3: 커밋**

```bash
git add backend/tests/test_fetcher_db.py
git commit -m "test: services 테스트 mock 대상을 provider 기반으로 수정"
```
