"""백테스트 통합 테스트 - 소규모 모의 데이터."""

import pandas as pd
import pytest

from src.engine.backtest import BacktestParams, BacktestResult, run_backtest


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


def _make_listing(codes: list[str], names: list[str], caps: list[int]) -> pd.DataFrame:
    """테스트용 종목 목록 DataFrame을 생성한다."""
    return pd.DataFrame({
        "Code": codes,
        "Name": names,
        "Marcap": caps,
    })


class TestRunBacktest:
    def test_basic_buy_and_sell(self):
        """3일 연속 상승 → 매수, 3일 연속 하락 → 매도 시나리오."""
        # 3일 상승 후 3일 하락
        prices = [100, 101, 102, 103, 102, 101, 100, 99, 105]
        price_data = {"A": _make_price_df(prices)}
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-15",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days=3,
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
            m_fall_days=3,
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
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-08",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days=3,
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
            [100_000_000, 10_000_000_000],
        )

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-08",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days=3,
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
        listing = _make_listing(["A"], ["테스트"], [1_000_000_000])

        params = BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-15",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days=3,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
        )

        result = run_backtest(params, price_data, listing)

        # MDD는 0 이하여야 함 (하락을 의미)
        assert result.mdd_pct <= 0
