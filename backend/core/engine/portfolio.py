"""포트폴리오 상태 관리 모듈 - 현금, 보유종목, 거래내역."""

from dataclasses import dataclass, field
from math import floor


@dataclass
class Trade:
    """개별 거래 기록."""
    date: str
    code: str
    name: str
    side: str  # "BUY" or "SELL"
    price: float
    quantity: int
    amount: float
    fee: float
    profit: float = 0.0  # 매도 시 실현 손익


@dataclass
class Holding:
    """보유 종목 정보."""
    code: str
    name: str
    quantity: int
    avg_price: float  # 평균 매입 단가


@dataclass
class DailySnapshot:
    """일별 자산 현황."""
    date: str
    cash: float
    stock_value: float
    total_value: float


@dataclass
class Portfolio:
    """포트폴리오 전체 상태."""
    cash: float
    fee_rate: float  # 수수료율 (예: 0.015는 0.015%)
    holdings: dict[str, Holding] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)
    daily_snapshots: list[DailySnapshot] = field(default_factory=list)

    def buy(self, date: str, code: str, name: str, price: float,
            max_amount: float, min_balance: float) -> bool:
        """종목을 매수한다.

        Args:
            date: 거래일
            code: 종목코드
            name: 종목명
            price: 매수 단가
            max_amount: 종목당 최대 매수 금액
            min_balance: 매수 후 최소 잔고

        Returns:
            매수 성공 여부
        """
        if price <= 0:
            return False

        available = self.cash - min_balance
        if available <= 0:
            return False

        buy_amount = min(max_amount, available)
        quantity = floor(buy_amount / price)
        if quantity <= 0:
            return False

        amount = quantity * price
        fee = amount * (self.fee_rate / 100)
        total_cost = amount + fee

        if total_cost > self.cash - min_balance:
            quantity = floor((available - fee) / price)
            if quantity <= 0:
                return False
            amount = quantity * price
            fee = amount * (self.fee_rate / 100)
            total_cost = amount + fee

        if total_cost > self.cash:
            return False

        self.cash -= total_cost

        if code in self.holdings:
            h = self.holdings[code]
            total_qty = h.quantity + quantity
            h.avg_price = (h.avg_price * h.quantity + amount) / total_qty
            h.quantity = total_qty
        else:
            self.holdings[code] = Holding(
                code=code, name=name, quantity=quantity, avg_price=price
            )

        self.trades.append(Trade(
            date=date, code=code, name=name, side="BUY",
            price=price, quantity=quantity, amount=amount, fee=fee,
        ))
        return True

    def sell_all(self, date: str, code: str, name: str, price: float) -> bool:
        """보유 종목을 전량 매도한다.

        Returns:
            매도 성공 여부
        """
        if code not in self.holdings:
            return False

        h = self.holdings[code]
        quantity = h.quantity
        amount = quantity * price
        fee = amount * (self.fee_rate / 100)
        net_amount = amount - fee

        profit = net_amount - (h.avg_price * quantity)

        self.cash += net_amount
        del self.holdings[code]

        self.trades.append(Trade(
            date=date, code=code, name=name, side="SELL",
            price=price, quantity=quantity, amount=amount, fee=fee,
            profit=profit,
        ))
        return True

    def snapshot(self, date: str, prices: dict[str, float]) -> DailySnapshot:
        """일별 자산 현황을 기록하고 반환한다.

        Args:
            date: 기준일
            prices: {종목코드: 종가} 딕셔너리
        """
        stock_value = sum(
            h.quantity * prices.get(h.code, h.avg_price)
            for h in self.holdings.values()
        )
        snap = DailySnapshot(
            date=date,
            cash=self.cash,
            stock_value=stock_value,
            total_value=self.cash + stock_value,
        )
        self.daily_snapshots.append(snap)
        return snap
