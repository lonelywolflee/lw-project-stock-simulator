"""Pydantic 스키마 - 백테스트 API 요청/응답."""

from typing import Literal

from ninja import Schema


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


class TradeSchema(Schema):
    """개별 거래 기록."""

    date: str
    code: str
    name: str
    side: str
    price: float
    quantity: int
    amount: float
    fee: float
    profit: float


class DailySnapshotSchema(Schema):
    """일별 자산 현황."""

    date: str
    cash: float
    stock_value: float
    total_value: float


class MarketIndexSchema(Schema):
    """시장 지수 데이터 (직렬화용)."""

    dates: list[str]
    values: list[float]


class BacktestResultSchema(Schema):
    """백테스트 전체 결과."""

    daily_snapshots: list[DailySnapshotSchema]
    trades: list[TradeSchema]
    kospi_index: MarketIndexSchema | None = None
    final_return_pct: float
    mdd_pct: float
    total_trades: int
    win_rate_pct: float
    total_fee: float
    execution_time: float = 0.0
