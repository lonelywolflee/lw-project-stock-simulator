"""시장 데이터 스키마."""

from ninja import Schema


class StockSchema(Schema):
    market: str
    code: str
    name: str
    listing_shares: int | None = None
