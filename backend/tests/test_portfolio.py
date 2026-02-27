"""포트폴리오 매수/매도/수수료 계산 테스트."""

import pytest

from core.engine.portfolio import Portfolio


class TestBuy:
    def test_basic_buy(self):
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        result = p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        assert result is True
        assert "005930" in p.holdings
        assert p.holdings["005930"].quantity == 71  # floor(5_000_000 / 70_000)
        assert p.cash < 10_000_000
        assert len(p.trades) == 1
        assert p.trades[0].side == "BUY"

    def test_buy_respects_min_balance(self):
        p = Portfolio(cash=2_000_000, fee_rate=0.015)
        result = p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_500_000)
        assert result is True
        # 사용 가능: 2M - 1.5M = 500K → 수량 = floor(500_000/70_000) = 7
        assert p.holdings["005930"].quantity == 7
        assert p.cash >= 1_500_000

    def test_buy_insufficient_funds(self):
        p = Portfolio(cash=1_000_000, fee_rate=0.015)
        result = p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        assert result is False
        assert "005930" not in p.holdings

    def test_buy_zero_price(self):
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        result = p.buy("2024-01-02", "005930", "삼성전자", 0, 5_000_000, 1_000_000)
        assert result is False

    def test_buy_adds_to_existing_holding(self):
        p = Portfolio(cash=20_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        qty1 = p.holdings["005930"].quantity
        p.buy("2024-01-03", "005930", "삼성전자", 72000, 5_000_000, 1_000_000)
        assert p.holdings["005930"].quantity > qty1


class TestSellAll:
    def test_basic_sell(self):
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        cash_after_buy = p.cash

        result = p.sell_all("2024-01-05", "005930", "삼성전자", 75000)
        assert result is True
        assert "005930" not in p.holdings
        assert p.cash > cash_after_buy
        sell_trade = [t for t in p.trades if t.side == "SELL"][0]
        assert sell_trade.profit > 0

    def test_sell_nonexistent(self):
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        result = p.sell_all("2024-01-05", "005930", "삼성전자", 75000)
        assert result is False

    def test_sell_at_loss(self):
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        p.sell_all("2024-01-05", "005930", "삼성전자", 60000)
        sell_trade = [t for t in p.trades if t.side == "SELL"][0]
        assert sell_trade.profit < 0


class TestSnapshot:
    def test_snapshot_with_holdings(self):
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        p.buy("2024-01-02", "005930", "삼성전자", 70000, 5_000_000, 1_000_000)
        snap = p.snapshot("2024-01-02", {"005930": 71000})
        assert snap.stock_value > 0
        assert snap.total_value == snap.cash + snap.stock_value
        assert len(p.daily_snapshots) == 1

    def test_snapshot_no_holdings(self):
        p = Portfolio(cash=10_000_000, fee_rate=0.015)
        snap = p.snapshot("2024-01-02", {})
        assert snap.stock_value == 0
        assert snap.total_value == 10_000_000


class TestFeeCalculation:
    def test_fee_deducted_on_buy(self):
        p = Portfolio(cash=10_000_000, fee_rate=1.0)  # 1% 수수료
        p.buy("2024-01-02", "005930", "삼성전자", 10000, 5_000_000, 0)
        trade = p.trades[0]
        expected_fee = trade.amount * 0.01
        assert abs(trade.fee - expected_fee) < 1

    def test_fee_deducted_on_sell(self):
        p = Portfolio(cash=10_000_000, fee_rate=1.0)
        p.buy("2024-01-02", "005930", "삼성전자", 10000, 5_000_000, 0)
        p.sell_all("2024-01-05", "005930", "삼성전자", 10000)
        sell_trade = [t for t in p.trades if t.side == "SELL"][0]
        expected_fee = sell_trade.amount * 0.01
        assert abs(sell_trade.fee - expected_fee) < 1


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
