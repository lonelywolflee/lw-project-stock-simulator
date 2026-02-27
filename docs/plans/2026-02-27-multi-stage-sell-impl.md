# 다단계 매도 시그널 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 기존 단일 구간 매도를 2단계 매도(1차 부분 매도 → 2차 전량 매도)로 확장한다.

**Architecture:** `signals.py`는 변경 없이 재활용하고, `portfolio.py`에 부분 매도 메서드를 추가하며, `backtest.py`에서 1차/2차 시그널을 사전 계산하고 `phase1_sold` 상태를 추적하는 방식으로 구현한다. API 스키마와 프론트엔드 폼도 새 파라미터에 맞게 갱신한다.

**Tech Stack:** Python (pandas, dataclass), Django Ninja (Pydantic Schema), React (react-hook-form, zod), TypeScript

**Design doc:** `docs/plans/2026-02-27-multi-stage-sell-design.md`

---

### Task 1: Portfolio `sell_partial()` 메서드 추가

**Files:**
- Modify: `backend/core/engine/portfolio.py`
- Test: `backend/tests/test_portfolio.py`

**Step 1: 실패하는 테스트 작성**

`backend/tests/test_portfolio.py` 끝에 추가:

```python
class TestSellPartial:
    def test_basic_partial_sell(self):
        """50% 부분 매도 시 수량이 절반으로 줄어야 한다."""
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        original_qty = p.holdings["005930"].quantity  # 71

        result = p.sell_partial("2024-01-05", "005930", "삼성전자", 75000, ratio=50)
        assert result is True
        assert "005930" in p.holdings
        expected_sold = round(original_qty * 50 / 100)  # 36 (반올림)
        assert p.holdings["005930"].quantity == original_qty - expected_sold
        sell_trade = [t for t in p.trades if t.side == "SELL"][0]
        assert sell_trade.quantity == expected_sold

    def test_partial_sell_rounds(self):
        """매도 수량은 반올림되어야 한다."""
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        original_qty = p.holdings["005930"].quantity  # 71

        result = p.sell_partial("2024-01-05", "005930", "삼성전자", 75000, ratio=30)
        assert result is True
        expected_sold = round(original_qty * 30 / 100)  # round(21.3) = 21
        assert p.holdings["005930"].quantity == original_qty - expected_sold

    def test_partial_sell_nonexistent(self):
        """미보유 종목 부분 매도는 실패해야 한다."""
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        result = p.sell_partial("2024-01-05", "005930", "삼성전자", 75000, ratio=50)
        assert result is False

    def test_partial_sell_records_profit(self):
        """부분 매도 시 매도 수량 기준으로 손익이 기록되어야 한다."""
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        p.sell_partial("2024-01-05", "005930", "삼성전자", 75000, ratio=50)
        sell_trade = [t for t in p.trades if t.side == "SELL"][0]
        assert sell_trade.profit > 0  # 70000 → 75000 이익

    def test_partial_sell_preserves_avg_price(self):
        """부분 매도 후 남은 보유분의 평균 매입가는 변하지 않아야 한다."""
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        avg_before = p.holdings["005930"].avg_price
        p.sell_partial("2024-01-05", "005930", "삼성전자", 75000, ratio=50)
        assert p.holdings["005930"].avg_price == avg_before

    def test_partial_sell_100_removes_holding(self):
        """100% 부분 매도는 전량 매도와 같아야 한다."""
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        result = p.sell_partial("2024-01-05", "005930", "삼성전자", 75000, ratio=100)
        assert result is True
        assert "005930" not in p.holdings
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_portfolio.py::TestSellPartial -v`
Expected: FAIL — `sell_partial` 메서드 없음

**Step 3: `sell_partial` 구현**

`backend/core/engine/portfolio.py`의 `Portfolio` 클래스에 `sell_all` 뒤에 추가:

```python
def sell_partial(self, date: str, code: str, name: str, price: float,
                 ratio: int) -> bool:
    """보유 종목의 일부를 매도한다.

    Args:
        date: 거래일
        code: 종목코드
        name: 종목명
        price: 매도 단가
        ratio: 매도 비율 (1~100, 반올림 적용)

    Returns:
        매도 성공 여부
    """
    if code not in self.holdings:
        return False

    h = self.holdings[code]
    sell_qty = round(h.quantity * ratio / 100)
    if sell_qty <= 0:
        return False

    if sell_qty >= h.quantity:
        return self.sell_all(date, code, name, price)

    amount = sell_qty * price
    fee = amount * (self.fee_rate / 100)
    net_amount = amount - fee
    profit = net_amount - (h.avg_price * sell_qty)

    self.cash += net_amount
    h.quantity -= sell_qty

    self.trades.append(Trade(
        date=date, code=code, name=name, side="SELL",
        price=price, quantity=sell_qty, amount=amount, fee=fee,
        profit=profit,
    ))
    return True
```

**Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_portfolio.py -v`
Expected: ALL PASS

**Step 5: 커밋**

```
feat: Portfolio에 sell_partial() 부분 매도 메서드 추가
```

---

### Task 2: `BacktestParams` 파라미터 변경 + `_precompute_signals` 확장

**Files:**
- Modify: `backend/core/engine/backtest.py`
- Test: `backend/tests/test_backtest.py`

**Step 1: `BacktestParams` 필드 변경**

`backend/core/engine/backtest.py`에서 `m_fall_days` 필드를 3개로 교체:

```python
@dataclass
class BacktestParams:
    """백테스트 실행 파라미터."""
    initial_cash: float
    start_date: str
    end_date: str
    fee_rate: float
    n_rise_days: int
    m_fall_days_1: int        # 1차 매도: 연속 하락 일수
    m_fall_days_2: int        # 2차 매도: 연속 하락 일수 (1차 포함)
    sell_ratio_1: int          # 1차 매도 비율 (10~90%)
    y_emergency_pct: float
    max_buy_amount: float
    min_balance: float
    sort_method: str = "market_cap"
```

**Step 2: `_precompute_signals` 변경**

시그니처와 내부를 수정하여 1차/2차 시그널을 각각 계산:

```python
def _precompute_signals(
    price_data: dict[str, pd.DataFrame],
    n_rise: int,
    m_fall_1: int,
    m_fall_2: int,
    y_pct: float,
) -> dict[str, dict[str, pd.Series]]:
    """모든 종목의 시그널을 사전 계산한다."""
    signals = {}
    for code, df in price_data.items():
        if "Close" not in df.columns or df.empty:
            continue
        close = df["Close"]
        signals[code] = {
            "buy": detect_consecutive_rises(close, n_rise),
            "sell_fall_1": detect_consecutive_falls(close, m_fall_1),
            "sell_fall_2": detect_consecutive_falls(close, m_fall_2),
            "sell_emergency": detect_emergency_sell(close, y_pct),
        }
    return signals
```

**Step 3: 기존 테스트의 파라미터 일괄 수정**

`backend/tests/test_backtest.py`에서 모든 `BacktestParams` 생성을 수정:

- `m_fall_days=3` → `m_fall_days_1=3, m_fall_days_2=5, sell_ratio_1=50`

**Step 4: 테스트 통과 확인 (아직 SELL 로직은 변경 전이므로 일부 실패 가능)**

Run: `cd backend && uv run pytest tests/test_backtest.py -v`

이 시점에서 SELL 로직이 아직 `sell_fall` 키를 참조하므로 KeyError 발생 예상. Task 3에서 해결.

**Step 5: 커밋**

```
refactor: BacktestParams를 다단계 매도 파라미터로 변경
```

---

### Task 3: SELL 단계 2단계 로직 구현

**Files:**
- Modify: `backend/core/engine/backtest.py`
- Test: `backend/tests/test_backtest.py`

**Step 1: 다단계 매도 전용 테스트 작성**

`backend/tests/test_backtest.py`에 추가:

```python
class TestMultiStageSell:
    def test_phase1_partial_sell(self):
        """1차 기간 도달 시 sell_ratio_1% 부분 매도."""
        # 3일 상승 → 3일 하락 (1차), 총 6일 데이터
        prices = [100, 101, 102, 103, 102, 101, 100]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-12",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=50,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        sell_trades = [t for t in result.trades if t.side == "SELL"]
        assert len(sell_trades) == 1  # 1차 부분 매도만 발생
        buy_trade = [t for t in result.trades if t.side == "BUY"][0]
        expected_sold = round(buy_trade.quantity * 50 / 100)
        assert sell_trades[0].quantity == expected_sold

    def test_phase2_full_sell(self):
        """2차 기간 도달 시 남은 수량 전량 매도."""
        # 3일 상승 → 5일 연속 하락 (1차+2차)
        prices = [100, 101, 102, 103, 102, 101, 100, 99, 98]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-15",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=50,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        sell_trades = [t for t in result.trades if t.side == "SELL"]
        assert len(sell_trades) == 2  # 1차 부분 + 2차 전량

    def test_phase1_skip_small_position(self):
        """보유 평가액이 threshold 이하면 1차 매도 스킵."""
        # 소액 포지션: max_buy_amount=200_000, sell_ratio_1=50 → threshold=100_000
        prices = [100, 101, 102, 103, 102, 101, 100, 99, 98]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-15",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=50,
            y_emergency_pct=5.0,
            max_buy_amount=200_000,  # 소액
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        sell_trades = [t for t in result.trades if t.side == "SELL"]
        # 1차 스킵 + 2차 전량매도 = 매도 1건
        if len(sell_trades) > 0:
            # 1차 매도가 스킵되었으므로 첫 매도가 전량 매도여야 함
            buy_trade = [t for t in result.trades if t.side == "BUY"][0]
            assert sell_trades[0].quantity == buy_trade.quantity

    def test_reset_after_rise(self):
        """연속 하락이 끊기면 1차 상태가 리셋되어야 한다."""
        # 3일 상승 → 3일 하락(1차) → 1일 상승(리셋) → 3일 하락(다시 1차)
        prices = [100, 101, 102, 103, 102, 101, 100, 101, 100, 99, 98]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-18",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=50,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        sell_trades = [t for t in result.trades if t.side == "SELL"]
        # 1차 매도 2회 (리셋 후 다시 발동)
        assert len(sell_trades) >= 2

    def test_emergency_sell_overrides_multi_stage(self):
        """긴급 손절은 다단계 매도 상태와 관계없이 전량 매도."""
        # 3일 상승 → 3일 하락(1차) → 급락(-10%)
        prices = [100, 101, 102, 103, 102, 101, 100, 88]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-15",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=50,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        # 최종적으로 보유 종목이 없어야 함 (긴급 손절로 전량 매도)
        sell_trades = [t for t in result.trades if t.side == "SELL"]
        total_sold = sum(t.quantity for t in sell_trades)
        buy_qty = sum(t.quantity for t in result.trades if t.side == "BUY")
        assert total_sold == buy_qty
```

**Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_backtest.py::TestMultiStageSell -v`
Expected: FAIL

**Step 3: SELL 단계 로직 구현**

`backend/core/engine/backtest.py`의 `run_backtest` 함수에서 SELL Phase를 전면 교체:

```python
def run_backtest(params, price_data, listing_df=None, kospi_df=None, event_callback=None):
    portfolio = Portfolio(cash=params.initial_cash, fee_rate=params.fee_rate)

    name_map: dict[str, str] = {}
    if listing_df is not None:
        if "Code" in listing_df.columns and "Name" in listing_df.columns:
            name_map = dict(zip(listing_df["Code"], listing_df["Name"]))

    signals = _precompute_signals(
        price_data, params.n_rise_days,
        params.m_fall_days_1, params.m_fall_days_2,
        params.y_emergency_pct,
    )

    trading_dates = _get_trading_dates(price_data)
    total_days = len(trading_dates)

    # 1차 매도 완료 상태 추적
    phase1_sold: set[str] = set()

    for day_idx, date in enumerate(trading_dates):
        date_str = date.strftime("%Y-%m-%d")

        # ── SELL Phase ──
        codes_to_sell_all: set[str] = set()
        codes_to_sell_partial: set[str] = set()

        for code in list(portfolio.holdings.keys()):
            if code not in signals:
                continue
            sig = signals[code]

            # 긴급 매도 (최우선)
            if date in sig["sell_emergency"].index and sig["sell_emergency"].get(date, False):
                codes_to_sell_all.add(code)
                continue

            # 2차 매도 (전량)
            if date in sig["sell_fall_2"].index and sig["sell_fall_2"].get(date, False):
                codes_to_sell_all.add(code)
                continue

            # 1차 매도 (부분) — 아직 1차 미실행인 경우만
            if code not in phase1_sold:
                if date in sig["sell_fall_1"].index and sig["sell_fall_1"].get(date, False):
                    codes_to_sell_partial.add(code)
                    continue

            # 1차 시그널이 꺼지면(연속 하락 끊김) phase1_sold 리셋
            if code in phase1_sold:
                is_still_falling = (
                    date in sig["sell_fall_1"].index
                    and sig["sell_fall_1"].get(date, False)
                )
                if not is_still_falling:
                    phase1_sold.discard(code)

        # 전량 매도 실행
        for code in codes_to_sell_all:
            if code not in price_data or date not in price_data[code].index:
                continue
            price = price_data[code].loc[date, "Close"]
            name = name_map.get(code, code)
            holding = portfolio.holdings.get(code)
            avg_price = holding.avg_price if holding else price
            if portfolio.sell_all(date_str, code, name, price):
                phase1_sold.discard(code)
                if event_callback:
                    profit_pct = round((price - avg_price) / avg_price * 100, 1) if avg_price > 0 else 0.0
                    event_callback({
                        "type": "trade", "side": "SELL",
                        "date": date_str, "name": name, "code": code,
                        "price": price, "profit_pct": profit_pct,
                    })

        # 1차 부분 매도 실행
        for code in codes_to_sell_partial:
            if code in codes_to_sell_all:
                continue
            if code not in price_data or date not in price_data[code].index:
                continue
            price = price_data[code].loc[date, "Close"]
            name = name_map.get(code, code)
            holding = portfolio.holdings.get(code)
            if not holding:
                continue

            # 소액 스킵 조건
            position_value = holding.quantity * price
            threshold = params.max_buy_amount * params.sell_ratio_1 / 100
            if position_value <= threshold:
                phase1_sold.add(code)
                continue

            avg_price = holding.avg_price
            if portfolio.sell_partial(date_str, code, name, price, params.sell_ratio_1):
                phase1_sold.add(code)
                if event_callback:
                    profit_pct = round((price - avg_price) / avg_price * 100, 1) if avg_price > 0 else 0.0
                    event_callback({
                        "type": "trade", "side": "SELL",
                        "date": date_str, "name": name, "code": code,
                        "price": price, "profit_pct": profit_pct,
                    })

        # ── BUY Phase ── (변경 없음)
        # ... (기존 코드 유지)
```

**Step 4: 전체 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

**Step 5: 커밋**

```
feat: 다단계 매도 로직 구현 (1차 부분 매도 + 2차 전량 매도)
```

---

### Task 4: API 스키마 변경

**Files:**
- Modify: `backend/apps/backtests/schemas.py`
- Modify: `backend/apps/backtests/api.py`

**Step 1: `BacktestParamsSchema` 수정**

```python
class BacktestParamsSchema(Schema):
    """백테스트 실행 파라미터."""

    initial_cash: float
    start_date: str
    end_date: str
    fee_rate: float = 0.015
    n_rise_days: int = 3
    m_fall_days_1: int = 3
    m_fall_days_2: int = 5
    sell_ratio_1: int = 50
    y_emergency_pct: float = 5.0
    max_buy_amount: float
    min_balance: float
    sort_method: Literal["market_cap", "return_rate"] = "market_cap"
```

**Step 2: `api.py`는 `params.dict()` → `BacktestParams(**params.dict())`로 자동 매핑되므로 변경 불필요. 필드명이 일치하는지 확인만.**

**Step 3: 커밋**

```
feat: API 스키마에 다단계 매도 파라미터 반영
```

---

### Task 5: Frontend 타입 및 폼 변경

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/forms/BacktestForm.tsx`

**Step 1: `types.ts` 수정**

```typescript
export interface BacktestParams {
  initial_cash: number;
  start_date: string;
  end_date: string;
  fee_rate: number;
  n_rise_days: number;
  m_fall_days_1: number;
  m_fall_days_2: number;
  sell_ratio_1: number;
  y_emergency_pct: number;
  max_buy_amount: number;
  min_balance: number;
  sort_method: "market_cap" | "return_rate";
}
```

**Step 2: `BacktestForm.tsx` zod 스키마 수정**

기존 `m_fall_days` 제거, 3개 필드 추가:

```typescript
const schema = z.object({
  // ... 기존 필드 ...
  m_fall_days_1: z.coerce.number().int().min(1).max(20),
  m_fall_days_2: z.coerce.number().int().min(2).max(30),
  sell_ratio_1: z.coerce.number().int().min(10).max(90),
  // ... 기존 필드 ...
}).refine((data) => new Date(data.start_date) < new Date(data.end_date), {
  message: "종료일은 시작일보다 이후여야 합니다",
  path: ["end_date"],
}).refine((data) => data.m_fall_days_2 > data.m_fall_days_1, {
  message: "2차 매도 기간은 1차보다 커야 합니다",
  path: ["m_fall_days_2"],
});
```

defaultValues:

```typescript
m_fall_days_1: 3,
m_fall_days_2: 5,
sell_ratio_1: 50,
```

**Step 3: 폼 UI — 전략 설정 섹션에서 기존 "연속 하락일" 입력을 3개로 교체**

```tsx
<div>
  <Label htmlFor="m_fall_days_1" className={labelClass}>1차 매도 연속 하락일</Label>
  <Input
    id="m_fall_days_1"
    type="number"
    min={1}
    max={20}
    className={inputClass}
    {...register("m_fall_days_1")}
  />
</div>
<div>
  <Label htmlFor="sell_ratio_1" className={labelClass}>1차 매도 비율 (%)</Label>
  <Input
    id="sell_ratio_1"
    type="number"
    min={10}
    max={90}
    className={inputClass}
    {...register("sell_ratio_1")}
  />
</div>
<div>
  <Label htmlFor="m_fall_days_2" className={labelClass}>2차 매도 연속 하락일 (전량)</Label>
  <Input
    id="m_fall_days_2"
    type="number"
    min={2}
    max={30}
    className={inputClass}
    {...register("m_fall_days_2")}
  />
  {errors.m_fall_days_2 && (
    <p className="mt-1 text-xs text-destructive">
      {errors.m_fall_days_2.message}
    </p>
  )}
</div>
```

**Step 4: 커밋**

```
feat: 프론트엔드에 다단계 매도 파라미터 UI 추가
```

---

### Task 6: 알고리즘 문서 갱신

**Files:**
- Modify: `docs/05-algorithm.md`

**Step 1: 매도 시그널 테이블, SELL 단계 설명, 입력 파라미터 테이블을 다단계 매도에 맞게 갱신**

주요 변경:
- 시그널 사전 계산 테이블에 `sell_fall_1`, `sell_fall_2` 추가
- SELL 단계를 1차/2차/긴급 3가지로 기술
- 파라미터 테이블에서 `m_fall_days` → `m_fall_days_1`, `m_fall_days_2`, `sell_ratio_1`

**Step 2: 커밋**

```
docs: 알고리즘 명세에 다단계 매도 반영
```
