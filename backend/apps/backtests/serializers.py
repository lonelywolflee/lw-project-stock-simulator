"""BacktestResult → JSON-serializable dict 변환."""


def serialize_snapshots(snapshots):
    return [
        {
            "date": s.date,
            "cash": s.cash,
            "stock_value": s.stock_value,
            "total_value": s.total_value,
        }
        for s in snapshots
    ]


def serialize_trades(trades):
    return [
        {
            "date": t.date,
            "code": t.code,
            "name": t.name,
            "side": t.side,
            "price": t.price,
            "quantity": t.quantity,
            "amount": t.amount,
            "fee": t.fee,
            "profit": t.profit,
            "market": t.market,
        }
        for t in trades
    ]


def serialize_index(df):
    """pandas DataFrame → {dates, values} 직렬화."""
    if df is None or df.empty:
        return None
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
        "values": df["Close"].tolist(),
    }


def serialize_result(result):
    """BacktestResult → JSON-serializable dict."""
    return {
        "daily_snapshots": serialize_snapshots(result.daily_snapshots),
        "trades": serialize_trades(result.trades),
        "kospi_index": serialize_index(result.kospi_index),
        "nasdaq_index": serialize_index(result.nasdaq_index),
        "initial_exchange_rate": result.initial_exchange_rate,
        "kospi_snapshots": serialize_snapshots(result.kospi_snapshots),
        "nasdaq_snapshots": serialize_snapshots(result.nasdaq_snapshots),
        "final_return_pct": result.final_return_pct,
        "mdd_pct": result.mdd_pct,
        "total_trades": result.total_trades,
        "win_rate_pct": result.win_rate_pct,
        "total_fee": result.total_fee,
    }
