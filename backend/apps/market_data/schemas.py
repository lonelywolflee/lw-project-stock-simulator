"""시장 데이터 스키마."""

from ninja import Schema


class StockSchema(Schema):
    market: str
    code: str
    name: str
    market_cap: int | None = None
