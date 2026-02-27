"""시장 데이터 API."""

from ninja import Router

from core.data.fetcher import fetch_stock_listing

from .schemas import StockSchema

router = Router()


@router.get("/stocks/{market}", response=list[StockSchema])
def list_stocks(request, market: str, limit: int = 100):
    """상장 종목 목록 조회."""
    df = fetch_stock_listing(market.upper())
    if df is None or df.empty:
        return []

    if market.upper() == "KOSPI":
        code_col, cap_col = "Code", "Marcap"
    else:
        code_col, cap_col = "Symbol", "MarketCap"

    records = []
    for _, row in df.head(limit).iterrows():
        records.append({
            "code": row.get(code_col, ""),
            "name": row.get("Name", ""),
            "market_cap": int(row.get(cap_col, 0)) if row.get(cap_col) else None,
        })
    return records
