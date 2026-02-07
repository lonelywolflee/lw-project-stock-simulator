"""백테스팅 코어 엔진 - 일별 루프 기반 시뮬레이션."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.engine.portfolio import Portfolio, DailySnapshot, Trade
from src.engine.signals import (
    detect_consecutive_falls,
    detect_consecutive_rises,
    detect_emergency_sell,
)


@dataclass
class BacktestParams:
    """백테스트 실행 파라미터."""
    initial_cash: float
    start_date: str
    end_date: str
    fee_rate: float         # 수수료율 (%)
    n_rise_days: int        # 매수 시그널: 연속 상승 일수
    m_fall_days: int        # 매도 시그널: 연속 하락 일수
    y_emergency_pct: float  # 긴급 매도: 급락 비율 (%)
    max_buy_amount: float   # 종목당 최대 매수 금액
    min_balance: float      # 매수 후 최소 잔고
    sort_method: str = "market_cap"  # "market_cap" or "return_rate"


@dataclass
class BacktestResult:
    """백테스트 결과."""
    daily_snapshots: list[DailySnapshot] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    kospi_index: pd.DataFrame | None = None
    final_return_pct: float = 0.0
    mdd_pct: float = 0.0
    total_trades: int = 0
    win_rate_pct: float = 0.0


def _precompute_signals(
    price_data: dict[str, pd.DataFrame],
    n_rise: int,
    m_fall: int,
    y_pct: float,
) -> dict[str, dict[str, pd.Series]]:
    """모든 종목의 시그널을 사전 계산한다."""
    signals = {}
    for code, df in price_data.items():
        if "Close" not in df.columns or df.empty:
            continue
        close = df["Close"]
        signals[code] = {
            "buy": detect_consecutive_rises(close, n_rise),
            "sell_fall": detect_consecutive_falls(close, m_fall),
            "sell_emergency": detect_emergency_sell(close, y_pct),
        }
    return signals


def _get_trading_dates(price_data: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """전체 종목 데이터에서 거래일 유니온을 구한다."""
    all_dates: set[pd.Timestamp] = set()
    for df in price_data.values():
        all_dates.update(df.index)
    return pd.DatetimeIndex(sorted(all_dates))


def _rank_buy_candidates(
    candidates: list[tuple[str, str, float]],
    price_data: dict[str, pd.DataFrame],
    listing_df: pd.DataFrame | None,
    sort_method: str,
    current_date: pd.Timestamp,
    n_rise: int,
) -> list[tuple[str, str, float]]:
    """매수 후보를 정렬한다.

    Args:
        candidates: [(code, name, price), ...]
        sort_method: "market_cap" 또는 "return_rate"
    """
    if sort_method == "market_cap" and listing_df is not None:
        cap_map = {}
        if "Code" in listing_df.columns and "Marcap" in listing_df.columns:
            cap_map = dict(zip(listing_df["Code"], listing_df["Marcap"]))
        elif "Code" in listing_df.columns and "MarketCap" in listing_df.columns:
            cap_map = dict(zip(listing_df["Code"], listing_df["MarketCap"]))
        candidates.sort(key=lambda x: cap_map.get(x[0], 0), reverse=True)
    elif sort_method == "return_rate":
        def get_return(item):
            code = item[0]
            if code in price_data:
                df = price_data[code]
                close = df["Close"]
                idx = close.index.get_indexer([current_date], method="ffill")
                if idx[0] >= n_rise:
                    start_price = close.iloc[idx[0] - n_rise]
                    end_price = close.iloc[idx[0]]
                    if start_price > 0:
                        return (end_price - start_price) / start_price
            return 0.0
        candidates.sort(key=get_return, reverse=True)
    return candidates


def _compute_metrics(portfolio: Portfolio, initial_cash: float) -> dict:
    """최종 지표를 계산한다."""
    snapshots = portfolio.daily_snapshots
    if not snapshots:
        return {"final_return_pct": 0.0, "mdd_pct": 0.0, "win_rate_pct": 0.0}

    total_values = pd.Series([s.total_value for s in snapshots])
    final_return = (total_values.iloc[-1] - initial_cash) / initial_cash * 100

    cummax = total_values.cummax()
    drawdown = (total_values - cummax) / cummax * 100
    mdd = drawdown.min()

    sell_trades = [t for t in portfolio.trades if t.side == "SELL"]
    if sell_trades:
        wins = sum(1 for t in sell_trades if t.profit > 0)
        win_rate = wins / len(sell_trades) * 100
    else:
        win_rate = 0.0

    return {
        "final_return_pct": round(final_return, 2),
        "mdd_pct": round(mdd, 2),
        "win_rate_pct": round(win_rate, 2),
    }


def run_backtest(
    params: BacktestParams,
    price_data: dict[str, pd.DataFrame],
    listing_df: pd.DataFrame | None = None,
    kospi_df: pd.DataFrame | None = None,
    progress_callback=None,
) -> BacktestResult:
    """백테스트를 실행한다.

    Args:
        params: 백테스트 파라미터
        price_data: {종목코드: 가격 DataFrame} 딕셔너리
        listing_df: KOSPI 상장 종목 목록 (시총 정렬용)
        kospi_df: KOSPI 지수 DataFrame (벤치마크)
        progress_callback: (current, total) 콜백

    Returns:
        BacktestResult
    """
    portfolio = Portfolio(cash=params.initial_cash, fee_rate=params.fee_rate)

    # 종목코드 → 종목명 매핑
    name_map: dict[str, str] = {}
    if listing_df is not None:
        if "Code" in listing_df.columns and "Name" in listing_df.columns:
            name_map = dict(zip(listing_df["Code"], listing_df["Name"]))

    # 시그널 사전 계산
    signals = _precompute_signals(
        price_data, params.n_rise_days, params.m_fall_days, params.y_emergency_pct
    )

    trading_dates = _get_trading_dates(price_data)
    total_days = len(trading_dates)

    for day_idx, date in enumerate(trading_dates):
        date_str = date.strftime("%Y-%m-%d")

        # ── SELL Phase ──
        codes_to_sell: set[str] = set()
        for code in list(portfolio.holdings.keys()):
            if code not in signals:
                continue
            sig = signals[code]

            # 연속 하락 매도
            if date in sig["sell_fall"].index and sig["sell_fall"].get(date, False):
                codes_to_sell.add(code)
            # 긴급 매도
            elif date in sig["sell_emergency"].index and sig["sell_emergency"].get(date, False):
                codes_to_sell.add(code)

        for code in codes_to_sell:
            if code not in price_data or date not in price_data[code].index:
                continue
            price = price_data[code].loc[date, "Close"]
            name = name_map.get(code, code)
            portfolio.sell_all(date_str, code, name, price)

        # ── BUY Phase ──
        buy_candidates: list[tuple[str, str, float]] = []
        for code, sig in signals.items():
            if code in portfolio.holdings:
                continue
            if date not in sig["buy"].index:
                continue
            if not sig["buy"].get(date, False):
                continue
            if code not in price_data or date not in price_data[code].index:
                continue
            price = price_data[code].loc[date, "Close"]
            name = name_map.get(code, code)
            buy_candidates.append((code, name, price))

        buy_candidates = _rank_buy_candidates(
            buy_candidates, price_data, listing_df,
            params.sort_method, date, params.n_rise_days,
        )

        for code, name, price in buy_candidates:
            if portfolio.cash < params.min_balance:
                break
            portfolio.buy(date_str, code, name, price,
                         params.max_buy_amount, params.min_balance)

        # ── SNAPSHOT ──
        current_prices = {}
        for code in portfolio.holdings:
            if code in price_data and date in price_data[code].index:
                current_prices[code] = price_data[code].loc[date, "Close"]
        portfolio.snapshot(date_str, current_prices)

        if progress_callback:
            progress_callback(day_idx + 1, total_days)

    metrics = _compute_metrics(portfolio, params.initial_cash)

    return BacktestResult(
        daily_snapshots=portfolio.daily_snapshots,
        trades=portfolio.trades,
        kospi_index=kospi_df,
        total_trades=len(portfolio.trades),
        **metrics,
    )
