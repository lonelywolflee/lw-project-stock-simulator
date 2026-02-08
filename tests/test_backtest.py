"""백테스트 통합 테스트 - 소규모 모의 데이터."""

import pandas as pd
import pytest

from src.engine.backtest import BacktestParams, BacktestResult, run_backtest, run_dual_market_backtest


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


def _make_exchange_rate_df(rate: float, start: str = "2024-01-01", periods: int = 15) -> pd.DataFrame:
    """테스트용 고정 환율 DataFrame을 생성한다."""
    dates = pd.date_range(start, periods=periods, freq="B")
    return pd.DataFrame(
        {"Close": [rate] * periods},
        index=dates,
    )


class TestDualMarketBacktest:
    def _base_params(self, kospi_ratio: int = 50) -> BacktestParams:
        return BacktestParams(
            initial_cash=10_000_000,
            start_date="2024-01-01",
            end_date="2024-01-15",
            fee_rate=0.015,
            n_rise_days=3,
            m_fall_days=3,
            y_emergency_pct=5.0,
            max_buy_amount=5_000_000,
            min_balance=1_000_000,
            kospi_ratio=kospi_ratio,
        )

    def test_dual_market_capital_split(self):
        """초기 자금이 비율대로 정확히 분배되는지 검증한다."""
        # 보합 데이터 (거래 없음) → 초기 자금 확인
        kospi_prices = {"K1": _make_price_df([100] * 9)}
        nasdaq_prices = {"N1": _make_price_df([50] * 9)}
        exchange_rate_df = _make_exchange_rate_df(1300.0)

        params = self._base_params(kospi_ratio=60)
        result = run_dual_market_backtest(
            params=params,
            kospi_price_data=kospi_prices,
            nasdaq_price_data=nasdaq_prices,
            kospi_listing_df=None,
            nasdaq_listing_df=None,
            kospi_df=None,
            nasdaq_df=None,
            exchange_rate_df=exchange_rate_df,
        )

        # KOSPI: 60% = 6,000,000 KRW
        assert len(result.kospi_snapshots) > 0
        assert result.kospi_snapshots[0].cash == pytest.approx(6_000_000, rel=1e-6)

        # NASDAQ: 40% = 4,000,000 KRW → 4,000,000/1300 USD
        assert len(result.nasdaq_snapshots) > 0
        expected_usd = 4_000_000 / 1300.0
        assert result.nasdaq_snapshots[0].cash == pytest.approx(expected_usd, rel=1e-6)

        # 합산 스냅샷의 첫 값 ≈ 초기 자본
        assert result.daily_snapshots[0].total_value == pytest.approx(10_000_000, rel=1e-4)

    def test_dual_market_independent_operation(self):
        """KOSPI/NASDAQ 포트폴리오가 독립적으로 운영되는지 검증한다."""
        # KOSPI: 3일 상승 → 매수 발생
        kospi_prices = {"K1": _make_price_df([100, 101, 102, 103, 104, 105, 106, 107, 108])}
        kospi_listing = _make_listing(["K1"], ["한국주식"], [1_000_000_000])

        # NASDAQ: 보합 → 거래 없음
        nasdaq_prices = {"N1": _make_price_df([50] * 9)}

        exchange_rate_df = _make_exchange_rate_df(1300.0)

        params = self._base_params(kospi_ratio=50)
        result = run_dual_market_backtest(
            params=params,
            kospi_price_data=kospi_prices,
            nasdaq_price_data=nasdaq_prices,
            kospi_listing_df=kospi_listing,
            nasdaq_listing_df=None,
            kospi_df=None,
            nasdaq_df=None,
            exchange_rate_df=exchange_rate_df,
        )

        # KOSPI에서만 매수 거래 발생
        kospi_trades = [t for t in result.trades if t.market == "KOSPI"]
        nasdaq_trades = [t for t in result.trades if t.market == "NASDAQ"]
        assert len(kospi_trades) > 0
        assert len(nasdaq_trades) == 0

        # NASDAQ 자금은 변화 없음 (현금 유지)
        for snap in result.nasdaq_snapshots:
            assert snap.stock_value == 0.0

    def test_dual_market_combined_snapshot_with_exchange_rate(self):
        """합산 스냅샷이 환율을 반영하여 정확한지 검증한다."""
        # 보합 데이터
        kospi_prices = {"K1": _make_price_df([100] * 5)}
        nasdaq_prices = {"N1": _make_price_df([50] * 5)}

        # 환율이 1300 → 1400으로 상승 (원화 약세)
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        rates = [1300, 1325, 1350, 1375, 1400]
        exchange_rate_df = pd.DataFrame({"Close": rates}, index=dates)

        params = self._base_params(kospi_ratio=50)
        result = run_dual_market_backtest(
            params=params,
            kospi_price_data=kospi_prices,
            nasdaq_price_data=nasdaq_prices,
            kospi_listing_df=None,
            nasdaq_listing_df=None,
            kospi_df=None,
            nasdaq_df=None,
            exchange_rate_df=exchange_rate_df,
        )

        # 환율 상승 → NASDAQ 부분의 원화 환산 가치 증가
        # 첫날 합산 = 5M(KOSPI) + 5M(NASDAQ KRW 환산) ≈ 10M
        first = result.daily_snapshots[0]
        assert first.total_value == pytest.approx(10_000_000, rel=1e-4)

        # 마지막 날: KOSPI 현금 동일, NASDAQ는 환율 상승분 반영
        last = result.daily_snapshots[-1]
        kospi_cash = 5_000_000
        nasdaq_usd = 5_000_000 / 1300.0
        expected_last = kospi_cash + nasdaq_usd * 1400.0
        assert last.total_value == pytest.approx(expected_last, rel=1e-4)

    def test_kospi_only_when_ratio_100(self):
        """ratio=100이면 KOSPI only로 동작한다."""
        prices = [100, 100, 100, 100, 100]
        price_data = {"A": _make_price_df(prices)}

        params = self._base_params(kospi_ratio=100)

        result = run_backtest(params, price_data)

        assert isinstance(result, BacktestResult)
        assert result.total_trades == 0
        # NASDAQ 관련 필드는 None
        assert result.nasdaq_index is None
        assert len(result.nasdaq_snapshots) == 0
