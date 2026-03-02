# KOSPI-DESC Fallback 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KOSPI 목록 조회 실패 시 KOSPI-DESC로 fallback하고, 시가총액이 없을 때 거래대금으로 대체 정렬한다.

**Architecture:** fetcher.py에서 KOSPI → KOSPI-DESC 순차 시도(각 retry=1). KOSPI-DESC는 Code, Name만 반환하므로 Marcap이 없다. backtest engine에서 Marcap 0인 종목은 volume×close로 대체. SSE log 이벤트로 사용자에게 안내.

**Tech Stack:** FinanceDataReader, pandas, Django, pytest

---

## Task 1: fetcher.py — KOSPI-DESC fallback 로직

**Files:**
- Modify: `backend/core/data/fetcher.py:32-63`
- Modify: `backend/tests/test_fetcher.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher.py`에 추가:

```python
from core.data.fetcher import fetch_stock_listing


class TestFetchStockListingFallback:
    def test_uses_kospi_on_success(self, mocker):
        """KOSPI 성공 시 그대로 반환한다."""
        mock_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"], "Marcap": [500_000_000_000],
        })
        mock_fdr = mocker.patch("core.data.fetcher.fdr.StockListing", return_value=mock_df)

        df = fetch_stock_listing("KOSPI")
        assert "Marcap" in df.columns
        assert len(df) == 1
        mock_fdr.assert_called_once_with("KOSPI")

    def test_falls_back_to_desc_on_kospi_failure(self, mocker):
        """KOSPI 실패 시 KOSPI-DESC로 fallback한다."""
        desc_df = pd.DataFrame({
            "Code": ["005930"], "Name": ["삼성전자"],
            "Market": ["KOSPI"], "Sector": ["전기전자"],
        })
        mocker.patch(
            "core.data.fetcher.fdr.StockListing",
            side_effect=[Exception("KRX down"), desc_df],
        )

        df = fetch_stock_listing("KOSPI")
        assert "Code" in df.columns
        assert "Name" in df.columns
        assert "Marcap" not in df.columns
        assert len(df) == 1

    def test_raises_when_both_fail(self, mocker):
        """KOSPI, KOSPI-DESC 둘 다 실패 시 예외."""
        mocker.patch(
            "core.data.fetcher.fdr.StockListing",
            side_effect=Exception("KRX down"),
        )

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")

    def test_listing_uses_retry_1(self, mocker):
        """listing은 retry=1을 사용한다."""
        mocker.patch(
            "core.data.fetcher.fdr.StockListing",
            side_effect=Exception("fail"),
        )
        mock_sleep = mocker.patch("core.data.fetcher.time.sleep")

        with pytest.raises(Exception):
            fetch_stock_listing("KOSPI")
        mock_sleep.assert_not_called()  # retry=1이면 sleep 없음
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_fetcher.py::TestFetchStockListingFallback -v`

**Step 3: 구현**

`backend/core/data/fetcher.py`의 `fetch_stock_listing` 수정:

```python
LISTING_RETRIES = 1

LISTING_FALLBACK_MARKETS = {
    "KOSPI": "KOSPI-DESC",
    "KOSDAQ": "KOSDAQ-DESC",
}


def _fetch_listing_with_fallback(market: str) -> pd.DataFrame:
    """목록 조회를 시도한다. 실패 시 DESC variant로 fallback."""
    try:
        return _retry(fdr.StockListing, market, retries=LISTING_RETRIES)
    except Exception as e:
        fallback = LISTING_FALLBACK_MARKETS.get(market)
        if fallback:
            logger.warning("종목 목록 %s 실패, %s로 fallback: %s", market, fallback, e)
            df = _retry(fdr.StockListing, fallback, retries=LISTING_RETRIES)
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
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_fetcher.py -v`

**Step 5: 커밋**

```bash
git add backend/core/data/fetcher.py backend/tests/test_fetcher.py
git commit -m "feat: fetch_stock_listing에 KOSPI-DESC fallback 추가 (retry=1)"
```

---

## Task 2: backtest engine — Marcap 0인 종목 volume×close 대체

**Files:**
- Modify: `backend/core/engine/backtest.py:75-110`
- Modify: `backend/tests/test_backtest.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_backtest.py`에 추가:

```python
class TestRankByCandidatesWithMissingMarcap:
    def test_uses_volume_times_close_when_marcap_zero(self, sample_price_data, sample_listing):
        """Marcap이 0이면 volume×close로 대체 정렬한다."""
        from core.engine.backtest import _rank_buy_candidates

        # listing에서 Marcap을 0으로 설정
        listing = sample_listing.copy()
        listing["Marcap"] = [0, 0]

        candidates = [
            ("A", "Stock A", 100.0),
            ("B", "Stock B", 200.0),
        ]
        current_date = pd.Timestamp("2024-01-04")

        result = _rank_buy_candidates(
            candidates, sample_price_data, listing,
            "market_cap", current_date, 2,
        )

        # volume×close가 큰 종목이 먼저
        # A: volume=3000, close=103 → 309000
        # B: volume=1500, close=203 → 304500
        assert result[0][0] == "A"

    def test_mixed_marcap_and_fallback(self, sample_price_data, sample_listing):
        """Marcap이 있는 종목과 없는 종목이 섞인 경우."""
        from core.engine.backtest import _rank_buy_candidates

        listing = sample_listing.copy()
        listing.loc[listing["Code"] == "A", "Marcap"] = 500_000_000_000
        listing.loc[listing["Code"] == "B", "Marcap"] = 0

        candidates = [
            ("B", "Stock B", 200.0),
            ("A", "Stock A", 100.0),
        ]
        current_date = pd.Timestamp("2024-01-04")

        result = _rank_buy_candidates(
            candidates, sample_price_data, listing,
            "market_cap", current_date, 2,
        )

        # A는 실제 시총 5000억 → B의 volume×close(약 30만)보다 큼
        assert result[0][0] == "A"
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_backtest.py::TestRankByCandidatesWithMissingMarcap -v`

**Step 3: 구현**

`backend/core/engine/backtest.py`의 `_rank_buy_candidates` 수정 (lines 89-95):

```python
    if sort_method == "market_cap" and listing_df is not None:
        cap_map = {}
        if "Code" in listing_df.columns and "Marcap" in listing_df.columns:
            cap_map = dict(zip(listing_df["Code"], listing_df["Marcap"]))
        elif "Code" in listing_df.columns and "MarketCap" in listing_df.columns:
            cap_map = dict(zip(listing_df["Code"], listing_df["MarketCap"]))

        def _effective_cap(code: str) -> float:
            cap = cap_map.get(code, 0) or 0
            if cap > 0:
                return float(cap)
            # Marcap 없으면 최신 거래일 volume × close로 대체
            if code in price_data and not price_data[code].empty:
                latest = price_data[code].iloc[-1]
                return float(latest["Volume"] * latest["Close"])
            return 0.0

        candidates.sort(key=lambda x: _effective_cap(x[0]), reverse=True)
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_backtest.py -v`

**Step 5: 커밋**

```bash
git add backend/core/engine/backtest.py backend/tests/test_backtest.py
git commit -m "feat: Marcap 없는 종목은 volume×close로 대체 정렬"
```

---

## Task 3: backtests/api.py — SSE 안내 문구

**Files:**
- Modify: `backend/apps/backtests/api.py:44-48`

**Step 1: 구현**

`backend/apps/backtests/api.py`의 Phase 1 섹션 (lines 44-48) 수정:

```python
            listing = fetch_stock_listing("KOSPI")
            codes = listing["Code"].tolist()

            has_marcap = "Marcap" in listing.columns
            if has_marcap:
                event_queue.put(("log", {
                    "message": f"✓ KOSPI {len(codes)}개 종목 로드",
                }))
            else:
                event_queue.put(("log", {
                    "message": f"⚠ KOSPI 목록 조회 실패로 KOSPI-DESC를 사용합니다. "
                               f"{len(codes)}개 종목 로드 (실시간 시가총액 미반영)",
                }))

            # ... Phase 3 이전에 추가 ...
            if not has_marcap and bp.sort_method == "market_cap":
                event_queue.put(("log", {
                    "message": "⚠ 시가총액 정보가 없는 종목은 거래대금(거래량×종가) 기준으로 산정합니다.",
                }))
```

**Step 2: 전체 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/ -v`

**Step 3: 커밋**

```bash
git add backend/apps/backtests/api.py
git commit -m "feat: KOSPI-DESC fallback 시 SSE 안내 문구 추가"
```

---

## Task 4: services 테스트 — mock 대상 수정

**Files:**
- Modify: `backend/tests/test_fetcher_db.py`

services 레이어 테스트 중 `core.data.fetcher._retry`를 mock하는 곳의 mock 대상을 `_fetch_listing_with_fallback`으로 변경한다.

**변경 대상 (4곳):**
- `TestFetchStockListingDB.test_fetches_from_network_when_no_batch` (line 39)
- `TestFetchStockListingDB.test_uses_db_fallback_on_network_error` (line 50)
- `TestFetchStockListingDB.test_raises_when_no_db_and_network_fails` (line 59)
- `TestIntegrationFlow.test_listing_then_price_flow` (line 259)

`mocker.patch("core.data.fetcher._retry", ...)` → `mocker.patch("core.data.fetcher._fetch_listing_with_fallback", ...)`

**Step 1: mock 대상 변경 + 테스트**

Run: `cd backend && uv run pytest tests/ -v`
Expected: 전체 PASS

**Step 2: 커밋**

```bash
git add backend/tests/test_fetcher_db.py
git commit -m "test: services 테스트 mock 대상을 _fetch_listing_with_fallback으로 수정"
```
