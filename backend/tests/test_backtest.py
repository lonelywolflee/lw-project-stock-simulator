"""백테스트 통합 테스트 - 소규모 모의 데이터."""

import pandas as pd
import pytest

from core.engine.backtest import BacktestParams, BacktestResult, run_backtest


def _make_price_df(prices: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    """테스트용 가격 DataFrame을 생성한다."""
    dates = pd.date_range(start, periods=len(prices), freq="B")
    return pd.DataFrame({
        "Open": prices,
        "High": prices,
        "Low": prices,
        "Close": prices,
        "Volume": [1000] * len(prices),
    }, index=dates)


def _make_listing(codes: list[str], names: list[str], shares: list[int]) -> pd.DataFrame:
    """테스트용 종목 목록 DataFrame을 생성한다."""
    return pd.DataFrame({
        "Code": codes,
        "Name": names,
        "Stocks": shares,
    })


@pytest.fixture
def sample_price_data():
    """테스트용 가격 데이터."""
    dates = pd.date_range("2024-01-02", periods=3, freq="B")
    return {
        "A": pd.DataFrame({
            "Open": [100, 101, 102], "High": [105, 106, 107],
            "Low": [99, 100, 101], "Close": [101, 102, 103],
            "Volume": [1000, 2000, 3000],
        }, index=dates),
        "B": pd.DataFrame({
            "Open": [200, 201, 202], "High": [205, 206, 207],
            "Low": [199, 200, 201], "Close": [201, 202, 203],
            "Volume": [500, 1000, 1500],
        }, index=dates),
    }


@pytest.fixture
def sample_listing():
    """테스트용 종목 목록."""
    return pd.DataFrame({
        "Code": ["A", "B"],
        "Name": ["Stock A", "Stock B"],
        "Stocks": [1_000_000, 2_000_000],
    })


class TestRankByCandidatesWithMissingStocks:
    def test_uses_volume_times_close_when_stocks_zero(self, sample_price_data, sample_listing):
        """Stocks가 0이면 volume*close로 대체 정렬한다."""
        from core.engine.backtest import _rank_buy_candidates

        # listing에서 Stocks를 0으로 설정
        listing = sample_listing.copy()
        listing["Stocks"] = [0, 0]

        # B를 먼저 넣어서 정렬 없이는 B가 먼저 나오도록 한다
        candidates = [
            ("B", "Stock B", 200.0),
            ("A", "Stock A", 100.0),
        ]
        current_date = pd.Timestamp("2024-01-04")

        result = _rank_buy_candidates(
            candidates, sample_price_data, listing,
            "market_cap", current_date, 2,
        )

        # volume*close가 큰 종목이 먼저
        # A: volume=3000, close=103 -> 309000
        # B: volume=1500, close=203 -> 304500
        assert result[0][0] == "A"

    def test_mixed_stocks_and_fallback(self, sample_price_data, sample_listing):
        """Stocks가 있는 종목과 없는 종목이 섞인 경우."""
        from core.engine.backtest import _rank_buy_candidates

        listing = sample_listing.copy()
        listing.loc[listing["Code"] == "A", "Stocks"] = 5_000_000_000
        listing.loc[listing["Code"] == "B", "Stocks"] = 0

        candidates = [
            ("B", "Stock B", 200.0),
            ("A", "Stock A", 100.0),
        ]
        current_date = pd.Timestamp("2024-01-04")

        result = _rank_buy_candidates(
            candidates, sample_price_data, listing,
            "market_cap", current_date, 2,
        )

        # A: 50억주 × 103원 = 약 5150억 → B의 volume*close(약 30만)보다 큼
        assert result[0][0] == "A"

    def test_volume_close_respects_current_date(self):
        """current_date 이후 데이터는 정렬에 반영하지 않는다."""
        from core.engine.backtest import _rank_buy_candidates

        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        price_data = {
            "A": pd.DataFrame({
                "Open": [100, 100, 100], "High": [100, 100, 100],
                "Low": [100, 100, 100], "Close": [100, 100, 100],
                "Volume": [100, 100, 5000],  # 마지막 날 급증
            }, index=dates),
            "B": pd.DataFrame({
                "Open": [100, 100, 100], "High": [100, 100, 100],
                "Low": [100, 100, 100], "Close": [100, 100, 100],
                "Volume": [200, 200, 200],
            }, index=dates),
        }
        listing = pd.DataFrame({
            "Code": ["A", "B"], "Name": ["A", "B"], "Stocks": [0, 0],
        })

        # current_date=첫째 날 → A:100*100=10000, B:200*100=20000 → B가 먼저
        candidates = [("A", "A", 100.0), ("B", "B", 100.0)]
        result = _rank_buy_candidates(
            candidates, price_data, listing,
            "market_cap", pd.Timestamp("2024-01-02"), 2,
        )
        assert result[0][0] == "B"

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


class TestRunBacktest:
    def test_basic_buy_and_sell(self):
        """3일 연속 상승 → 매수, 3일 연속 하락 → 매도 시나리오."""
        # 3일 상승 후 3일 하락
        prices = [100, 101, 102, 103, 102, 101, 100, 99, 105]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

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

        assert isinstance(result, BacktestResult)
        assert len(result.daily_snapshots) > 0
        assert result.total_trades > 0

        # 매수 거래가 있어야 함
        buy_trades = [t for t in result.trades if t.side == "BUY"]
        assert len(buy_trades) >= 1

    def test_no_trades_when_no_signals(self):
        """시그널이 발생하지 않으면 거래가 없어야 한다."""
        # 보합 데이터
        prices = [100, 100, 100, 100, 100]
        price_data = {"A": _make_price_df(prices)}

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-08",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=50,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data)

        assert result.total_trades == 0
        assert result.final_return_pct == 0.0

    def test_emergency_sell(self):
        """급락 시 긴급 매도가 발생해야 한다."""
        # 3일 상승 후 급락(-10%)
        prices = [100, 101, 102, 103, 92]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-08",
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
        assert len(sell_trades) >= 1

    def test_multiple_stocks_sorted_by_market_cap(self):
        """여러 종목이 있을 때 시총순으로 매수해야 한다."""
        prices_a = [100, 101, 102, 103, 104]
        prices_b = [200, 201, 202, 203, 204]
        price_data = {
            "A": _make_price_df(prices_a),
            "B": _make_price_df(prices_b),
        }
        listing = _make_listing(
            ["A", "B"], ["소형주", "대형주"],
            [100_000, 10_000_000],
        )

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-08",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=50,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
            sort_method="market_cap",
        )

        result = run_backtest(params, price_data, listing)

        buy_trades = [t for t in result.trades if t.side == "BUY"]
        if len(buy_trades) >= 2:
            # 대형주(B)가 먼저 매수되어야 함
            assert buy_trades[0].code == "B"

    def test_mdd_calculation(self):
        """MDD가 올바르게 계산되어야 한다."""
        # 상승 → 하락 → 회복 패턴
        prices = [100, 101, 102, 103, 95, 90, 85, 90, 95]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

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

        # MDD는 0 이하여야 함 (하락을 의미)
        assert result.mdd_pct <= 0

    def test_event_callback_reports_progress_and_trades(self):
        """event_callback이 progress와 trade 이벤트를 보고해야 한다."""
        prices = [100, 101, 102, 103, 102, 101, 100]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

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

        events = []
        result = run_backtest(params, price_data, listing, event_callback=events.append)

        # progress 이벤트가 있어야 함
        progress_events = [e for e in events if e["type"] == "progress"]
        assert len(progress_events) > 0

        # 매매가 발생했으면 trade 이벤트도 있어야 함
        if result.total_trades > 0:
            trade_events = [e for e in events if e["type"] == "trade"]
            assert len(trade_events) > 0

        # progress 이벤트에 필수 필드 확인
        p = progress_events[0]
        assert "current" in p
        assert "total" in p
        assert "date" in p


class TestMultiStageSell:
    def test_phase1_partial_sell(self):
        """1차 기간 도달 시 sell_ratio_1% 부분 매도."""
        # 3일 상승 → 3일 하락 (1차), 총 7일 데이터
        prices = [100, 101, 102, 103, 102, 101, 100]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

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
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

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
        # 소액 포지션: 잔고 제한으로 소량만 매수 → threshold보다 작아 1차 스킵
        # initial_cash=1_100_000, min_balance=1_000_000 → 매수 가능 금액 ~100,000
        # max_buy_amount=5_000_000, sell_ratio_1=50 → threshold=2,500,000
        # 매수 수량 = floor(100000/103) = 970주, 평가액 = 970*100 = 97,000 < 2,500,000
        prices = [100, 101, 102, 103, 102, 101, 100, 99, 98]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

        params = BacktestParams(
            initial_cash=1_100_000,
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
        # 1차 스킵 + 2차 전량매도 = 매도 1건
        assert len(sell_trades) == 1, f"Expected 1 sell (phase-1 skipped), got {len(sell_trades)}"
        buy_trade = [t for t in result.trades if t.side == "BUY"][0]
        assert sell_trades[0].quantity == buy_trade.quantity

    def test_reset_after_rise(self):
        """연속 하락이 끊기면 1차 상태가 리셋되어야 한다."""
        # 3일 상승 → 3일 하락(1차) → 1일 상승(리셋) → 3일 하락(다시 1차)
        # sell_ratio_1=25로 설정하여 1차 매도 후 남은 포지션이
        # threshold(max_buy_amount*25/100=1,250,000)를 초과하도록 함
        prices = [100, 101, 102, 103, 102, 101, 100, 101, 100, 99, 98]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-18",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=25,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        sell_trades = [t for t in result.trades if t.side == "SELL"]
        # 1차 매도 2회 (리셋 후 다시 발동)
        assert len(sell_trades) == 2

    def test_emergency_sell_overrides_multi_stage(self):
        """긴급 손절은 다단계 매도 상태와 관계없이 전량 매도."""
        # 3일 상승 → 3일 하락(1차) → 급락(-10%)
        prices = [100, 101, 102, 103, 102, 101, 100, 88]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

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

    def test_sell_ratio_zero_skips_phase1(self):
        """sell_ratio_1=0이면 1차 매도 없이 2차에서 바로 전량 매도."""
        # 3일 상승 → 5일 연속 하락
        prices = [100, 101, 102, 103, 102, 101, 100, 99, 98]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [10_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-15",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days_1=3,
            m_fall_days_2=5,
            sell_ratio_1=0,  # 1차 비활성화
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        sell_trades = [t for t in result.trades if t.side == "SELL"]
        # 1차 없이 2차 전량 매도 1건만 발생
        assert len(sell_trades) == 1
        buy_trade = [t for t in result.trades if t.side == "BUY"][0]
        assert sell_trades[0].quantity == buy_trade.quantity


