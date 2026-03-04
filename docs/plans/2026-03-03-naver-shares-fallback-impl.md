# 네이버 증권 상장주식수 Fallback 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 매수 후보 랭킹 시 listing_shares가 없는 종목에 대해 네이버 증권에서 상장주식수를 스크래핑하는 중간 fallback을 추가한다.

**Architecture:** backtest 엔진의 `_rank_buy_candidates`에 `resolve_shares` 콜백을 주입한다. 콜백은 DB 캐시(날짜 기준)를 먼저 확인하고, 캐시 미스 시 네이버 증권 HTML을 파싱하여 상장주식수를 가져온다. 결과는 DB에 저장하여 동일 종목의 반복 호출을 방지한다.

**Tech Stack:** Django ORM, requests, re (정규식 HTML 파싱)

---

### Task 1: StockListing 모델에 listing_shares_updated_at 필드 추가

**Files:**
- Modify: `backend/apps/market_data/models.py:20-35`
- Create: `backend/apps/market_data/migrations/0003_stocklisting_listing_shares_updated_at.py`

**Step 1: 모델에 필드 추가**

`backend/apps/market_data/models.py`의 `StockListing` 클래스에:

```python
listing_shares_updated_at = models.DateField(null=True, blank=True)
```

`listing_shares` 바로 아래에 추가.

**Step 2: 마이그레이션 생성**

```bash
cd backend && source .venv/bin/activate && echo "y" | python manage.py makemigrations market_data --name stocklisting_listing_shares_updated_at
```

**Step 3: 마이그레이션 적용 확인**

```bash
cd backend && source .venv/bin/activate && python manage.py migrate --run-syncdb
```

**Step 4: 커밋**

```bash
git add backend/apps/market_data/models.py backend/apps/market_data/migrations/0003_*.py
git commit -m "feat: StockListing에 listing_shares_updated_at 필드 추가"
```

---

### Task 2: 네이버 증권 스크래핑 함수 (TDD)

**Files:**
- Modify: `backend/core/data/fetcher.py`
- Modify: `backend/tests/test_fetcher.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher.py` 끝에 추가:

```python
class TestFetchListingSharesFromNaver:
    def test_parses_listing_shares(self, mocker):
        """네이버 증권 HTML에서 상장주식수를 파싱한다."""
        html = '''
        <div id="tab_con1" class="tab_con1" style="display:block">
        <table>
        <tr><th scope="row">상장주식수</th><td><em>5,969,782,550</em></td></tr>
        </table>
        </div>
        '''
        mock_resp = mocker.Mock()
        mock_resp.text = html
        mock_resp.raise_for_status = mocker.Mock()
        mocker.patch("core.data.fetcher.requests.get", return_value=mock_resp)

        from core.data.fetcher import fetch_listing_shares_from_naver

        result = fetch_listing_shares_from_naver("005930")
        assert result == 5_969_782_550

    def test_returns_none_on_network_error(self, mocker):
        """네트워크 오류 시 None을 반환한다."""
        mocker.patch("core.data.fetcher.requests.get", side_effect=Exception("timeout"))

        from core.data.fetcher import fetch_listing_shares_from_naver

        result = fetch_listing_shares_from_naver("005930")
        assert result is None

    def test_returns_none_on_parse_failure(self, mocker):
        """파싱 실패 시 None을 반환한다."""
        mock_resp = mocker.Mock()
        mock_resp.text = "<html><body>no data</body></html>"
        mock_resp.raise_for_status = mocker.Mock()
        mocker.patch("core.data.fetcher.requests.get", return_value=mock_resp)

        from core.data.fetcher import fetch_listing_shares_from_naver

        result = fetch_listing_shares_from_naver("005930")
        assert result is None
```

**Step 2: 테스트 실행 → 실패 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_fetcher.py::TestFetchListingSharesFromNaver -v
```

Expected: FAIL (ImportError — 함수 미정의)

**Step 3: 구현**

`backend/core/data/fetcher.py` 상단에 `import re`, `import requests` 추가.
파일 끝(`if __name__` 전)에 함수 추가:

```python
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
```

참고: `requests`는 이미 `FinanceDataReader`의 의존성으로 설치되어 있다. fetcher.py 상단에 import만 추가.

**Step 4: 테스트 실행 → 통과 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_fetcher.py::TestFetchListingSharesFromNaver -v
```

Expected: 3 passed

**Step 5: 커밋**

```bash
git add backend/core/data/fetcher.py backend/tests/test_fetcher.py
git commit -m "feat: 네이버 증권 상장주식수 스크래핑 함수 추가"
```

---

### Task 3: resolve 콜백 — DB 캐시 + 네이버 호출 (TDD)

**Files:**
- Modify: `backend/apps/market_data/services.py`
- Modify: `backend/tests/test_fetcher_db.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_fetcher_db.py` 끝에 추가:

```python
@pytest.mark.django_db
class TestResolveListingShares:
    def test_returns_cached_value_if_updated_today(self):
        """오늘 업데이트된 listing_shares는 네이버 호출 없이 반환한다."""
        from apps.market_data.services import resolve_listing_shares

        StockListing.objects.create(
            market="KOSPI", code="005930", name="삼성전자",
            listing_shares=5_969_782_550,
            listing_shares_updated_at=datetime.date.today(),
        )

        result = resolve_listing_shares("KOSPI", "005930")
        assert result == 5_969_782_550

    def test_fetches_from_naver_when_no_cache(self, mocker):
        """캐시 미스 시 네이버에서 가져와 DB에 저장한다."""
        from apps.market_data.services import resolve_listing_shares

        StockListing.objects.create(
            market="KOSPI", code="005930", name="삼성전자",
            listing_shares=None, listing_shares_updated_at=None,
        )
        mocker.patch(
            "apps.market_data.services._fetch_listing_shares_from_naver",
            return_value=5_969_782_550,
        )

        result = resolve_listing_shares("KOSPI", "005930")

        assert result == 5_969_782_550
        obj = StockListing.objects.get(code="005930")
        assert obj.listing_shares == 5_969_782_550
        assert obj.listing_shares_updated_at == datetime.date.today()

    def test_returns_none_when_naver_fails(self, mocker):
        """네이버도 실패하면 None을 반환한다."""
        from apps.market_data.services import resolve_listing_shares

        StockListing.objects.create(
            market="KOSPI", code="005930", name="삼성전자",
            listing_shares=None, listing_shares_updated_at=None,
        )
        mocker.patch(
            "apps.market_data.services._fetch_listing_shares_from_naver",
            return_value=None,
        )

        result = resolve_listing_shares("KOSPI", "005930")
        assert result is None

    def test_skips_naver_when_updated_today_even_if_zero(self):
        """오늘 업데이트했지만 shares가 None이면 None 반환 (재호출 안 함)."""
        from apps.market_data.services import resolve_listing_shares

        StockListing.objects.create(
            market="KOSPI", code="005930", name="삼성전자",
            listing_shares=None,
            listing_shares_updated_at=datetime.date.today(),
        )

        result = resolve_listing_shares("KOSPI", "005930")
        assert result is None

    def test_refetches_when_updated_yesterday(self, mocker):
        """어제 업데이트된 경우 네이버에서 다시 가져온다."""
        from apps.market_data.services import resolve_listing_shares

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        StockListing.objects.create(
            market="KOSPI", code="005930", name="삼성전자",
            listing_shares=5_000_000_000,
            listing_shares_updated_at=yesterday,
        )
        mocker.patch(
            "apps.market_data.services._fetch_listing_shares_from_naver",
            return_value=5_969_782_550,
        )

        result = resolve_listing_shares("KOSPI", "005930")

        assert result == 5_969_782_550
        obj = StockListing.objects.get(code="005930")
        assert obj.listing_shares == 5_969_782_550
```

**Step 2: 테스트 실행 → 실패 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_fetcher_db.py::TestResolveListingShares -v
```

Expected: FAIL (ImportError)

**Step 3: 구현**

`backend/apps/market_data/services.py`에 import 추가:

```python
from core.data.fetcher import (
    _fetch_index_with_fallback as _core_fetch_index_with_fallback,
    fetch_listing_shares_from_naver as _fetch_listing_shares_from_naver,
    fetch_price_data_raw as _core_fetch_price_data_raw,
    fetch_stock_listing as _core_fetch_stock_listing,
)
```

종목 목록 DB 콜백 섹션(`_mark_listing_batch_done` 뒤)에 함수 추가:

```python
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
```

**Step 4: 테스트 실행 → 통과 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_fetcher_db.py::TestResolveListingShares -v
```

Expected: 5 passed

**Step 5: 커밋**

```bash
git add backend/apps/market_data/services.py backend/tests/test_fetcher_db.py
git commit -m "feat: resolve_listing_shares DB 캐시 + 네이버 fallback 구현"
```

---

### Task 4: _save_listing_to_db에 updated_at 기록 추가

**Files:**
- Modify: `backend/apps/market_data/services.py:45-71`

**Step 1: _save_listing_to_db 수정**

FDR에서 일괄 저장 시 `listing_shares`가 있으면 `listing_shares_updated_at=today()`도 함께 저장.

`_save_listing_to_db` 함수에서 StockListing 객체 생성 부분 수정:

```python
objects.append(StockListing(
    market=market,
    code=code,
    name=row.get("Name", ""),
    listing_shares=int(row.get(shares_col, 0)) if has_shares and row.get(shares_col) else None,
    listing_shares_updated_at=datetime.date.today() if has_shares and row.get(shares_col) else None,
))
```

`update_fields` 부분도 수정:

```python
update_fields = ["name"]
if has_shares:
    update_fields.extend(["listing_shares", "listing_shares_updated_at"])
```

**Step 2: 기존 테스트 통과 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_fetcher_db.py::TestFetchStockListingDB -v
```

Expected: 4 passed

**Step 3: 커밋**

```bash
git add backend/apps/market_data/services.py
git commit -m "feat: FDR 일괄 저장 시 listing_shares_updated_at 기록"
```

---

### Task 5: backtest 엔진에 resolve_shares 콜백 주입 (TDD)

**Files:**
- Modify: `backend/core/engine/backtest.py:75-106, 154-161`
- Modify: `backend/tests/test_backtest.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_backtest.py`의 `TestRankByCandidatesWithMissingStocks` 클래스 끝에 추가:

```python
    def test_calls_resolve_shares_when_stocks_zero(self, sample_price_data, sample_listing):
        """Stocks가 0이면 resolve_shares 콜백을 호출한다."""
        from core.engine.backtest import _rank_buy_candidates

        listing = sample_listing.copy()
        listing["Stocks"] = [0, 0]

        resolve_calls = []

        def mock_resolve(code):
            resolve_calls.append(code)
            return {"A": 10_000_000, "B": 1_000_000}.get(code)

        candidates = [
            ("B", "Stock B", 200.0),
            ("A", "Stock A", 100.0),
        ]
        current_date = pd.Timestamp("2024-01-04")

        result = _rank_buy_candidates(
            candidates, sample_price_data, listing,
            "market_cap", current_date, 2,
            resolve_shares=mock_resolve,
        )

        # A: 10_000_000 × 103 = 1,030,000,000
        # B: 1_000_000 × 203 = 203,000,000
        assert result[0][0] == "A"
        assert set(resolve_calls) == {"A", "B"}

    def test_falls_back_to_volume_when_resolve_returns_none(self, sample_price_data, sample_listing):
        """resolve_shares도 None이면 volume*close fallback."""
        from core.engine.backtest import _rank_buy_candidates

        listing = sample_listing.copy()
        listing["Stocks"] = [0, 0]

        candidates = [
            ("B", "Stock B", 200.0),
            ("A", "Stock A", 100.0),
        ]
        current_date = pd.Timestamp("2024-01-04")

        result = _rank_buy_candidates(
            candidates, sample_price_data, listing,
            "market_cap", current_date, 2,
            resolve_shares=lambda code: None,
        )

        # resolve 실패 → volume*close fallback
        # A: 3000*103=309000, B: 1500*203=304500
        assert result[0][0] == "A"
```

**Step 2: 테스트 실행 → 실패 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_backtest.py::TestRankByCandidatesWithMissingStocks::test_calls_resolve_shares_when_stocks_zero -v
```

Expected: FAIL (unexpected keyword argument 'resolve_shares')

**Step 3: 구현**

`backend/core/engine/backtest.py`의 `_rank_buy_candidates` 시그니처 수정 (line 75-82):

```python
def _rank_buy_candidates(
    candidates: list[tuple[str, str, float]],
    price_data: dict[str, pd.DataFrame],
    listing_df: pd.DataFrame | None,
    sort_method: str,
    current_date: pd.Timestamp,
    n_rise: int,
    resolve_shares: Callable[[str], int | None] | None = None,
) -> list[tuple[str, str, float]]:
```

상단 import에 `Callable` 추가:

```python
from collections.abc import Callable
```

`_effective_cap` 함수 내부 수정 (line 94-104):

```python
def _effective_cap(code: str) -> float:
    shares = shares_map.get(code, 0) or 0
    if not shares and resolve_shares:
        shares = resolve_shares(code) or 0
    if code in price_data and not price_data[code].empty:
        available = price_data[code].loc[:current_date]
        if not available.empty:
            latest = available.iloc[-1]
            if shares > 0:
                return float(shares * latest["Close"])
            return float(latest["Volume"] * latest["Close"])
    return 0.0
```

`run_backtest` 시그니처에도 `resolve_shares` 추가 (line 154-161):

```python
def run_backtest(
    params: BacktestParams,
    price_data: dict[str, pd.DataFrame],
    listing_df: pd.DataFrame | None = None,
    kospi_df: pd.DataFrame | None = None,
    event_callback=None,
    resolve_shares: Callable[[str], int | None] | None = None,
) -> BacktestResult:
```

`run_backtest` 내부 `_rank_buy_candidates` 호출에 전달 (line 301-306 부근):

```python
buy_candidates = _rank_buy_candidates(
    buy_candidates, price_data, listing_df,
    params.sort_method, date, params.n_rise_days,
    resolve_shares=resolve_shares,
)
```

**Step 4: 테스트 실행 → 통과 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_backtest.py::TestRankByCandidatesWithMissingStocks -v
```

Expected: 5 passed (기존 3 + 신규 2)

**Step 5: 전체 테스트 통과 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
```

Expected: 전체 통과

**Step 6: 커밋**

```bash
git add backend/core/engine/backtest.py backend/tests/test_backtest.py
git commit -m "feat: _rank_buy_candidates에 resolve_shares 콜백 주입"
```

---

### Task 6: API에서 resolve_shares 콜백 주입

**Files:**
- Modify: `backend/apps/backtests/api.py:11-15, 96-99`

**Step 1: import 추가 및 콜백 주입**

`backend/apps/backtests/api.py`의 import에 `resolve_listing_shares` 추가:

```python
from apps.market_data.services import (
    fetch_all_prices,
    fetch_kospi_index,
    fetch_stock_listing,
    resolve_listing_shares,
)
```

`run_backtest` 호출 부분 (line 96-99) 수정:

```python
result = run_backtest(
    bp, prices, listing, kospi_index,
    event_callback=on_backtest_event,
    resolve_shares=lambda code: resolve_listing_shares("KOSPI", code),
)
```

**Step 2: 전체 테스트 통과 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
```

Expected: 전체 통과

**Step 3: 커밋**

```bash
git add backend/apps/backtests/api.py
git commit -m "feat: 백테스트 API에 resolve_shares 콜백 주입"
```

---

### Task 7: admin에 listing_shares_updated_at 표시

**Files:**
- Modify: `backend/apps/market_data/admin.py:16-19`

**Step 1: list_display에 필드 추가**

```python
@admin.register(StockListing)
class StockListingAdmin(ModelAdmin):
    list_display = ("market", "code", "name", "listing_shares", "listing_shares_updated_at")
    list_filter = ("market",)
    search_fields = ("code", "name")
```

**Step 2: 전체 테스트 통과 확인**

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -v
```

**Step 3: 커밋**

```bash
git add backend/apps/market_data/admin.py
git commit -m "feat: admin에 listing_shares_updated_at 표시 추가"
```

---

## 검증

1. `python -m pytest tests/ -v` — 전체 테스트 통과
2. 수동 검증:
   ```bash
   cd backend && source .venv/bin/activate
   python -c "from core.data.fetcher import fetch_listing_shares_from_naver; print(fetch_listing_shares_from_naver('005930'))"
   ```
   Expected: 삼성전자 상장주식수 출력 (예: 5969782550)
