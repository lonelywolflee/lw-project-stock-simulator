"""백테스팅 코어 엔진 - 일별 루프 기반 시뮬레이션."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.engine.portfolio import Portfolio, DailySnapshot, Trade
from core.engine.signals import (
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
    kospi_ratio: int = 100  # KOSPI 투자 비율 (0~100, 나머지는 NASDAQ)


@dataclass
class BacktestResult:
    """백테스트 결과."""
    daily_snapshots: list[DailySnapshot] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    kospi_index: pd.DataFrame | None = None
    nasdaq_index: pd.DataFrame | None = None
    exchange_rate_df: pd.DataFrame | None = None
    initial_exchange_rate: float = 0.0
    kospi_snapshots: list[DailySnapshot] = field(default_factory=list)
    nasdaq_snapshots: list[DailySnapshot] = field(default_factory=list)
    final_return_pct: float = 0.0
    mdd_pct: float = 0.0
    total_trades: int = 0
    win_rate_pct: float = 0.0
    total_fee: float = 0.0


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

    total_fee = sum(t.fee for t in portfolio.trades)

    return {
        "final_return_pct": round(final_return, 2),
        "mdd_pct": round(mdd, 2),
        "win_rate_pct": round(win_rate, 2),
        "total_fee": round(total_fee, 0),
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


def _compute_metrics_from_snapshots(
    snapshots: list[DailySnapshot],
    trades: list[Trade],
    initial_cash: float,
) -> dict:
    """스냅샷 리스트와 거래 리스트로부터 지표를 계산한다."""
    if not snapshots:
        return {"final_return_pct": 0.0, "mdd_pct": 0.0, "win_rate_pct": 0.0, "total_fee": 0.0}

    total_values = pd.Series([s.total_value for s in snapshots])
    final_return = (total_values.iloc[-1] - initial_cash) / initial_cash * 100

    cummax = total_values.cummax()
    drawdown = (total_values - cummax) / cummax * 100
    mdd = drawdown.min()

    sell_trades = [t for t in trades if t.side == "SELL"]
    if sell_trades:
        wins = sum(1 for t in sell_trades if t.profit > 0)
        win_rate = wins / len(sell_trades) * 100
    else:
        win_rate = 0.0

    total_fee = sum(t.fee for t in trades)

    return {
        "final_return_pct": round(final_return, 2),
        "mdd_pct": round(mdd, 2),
        "win_rate_pct": round(win_rate, 2),
        "total_fee": round(total_fee, 0),
    }


def _lookup_by_date(snapshots: list[DailySnapshot], date_str: str) -> DailySnapshot | None:
    """날짜 문자열로 스냅샷을 검색한다. 정확히 없으면 직전 값을 반환."""
    last = None
    for s in snapshots:
        if s.date <= date_str:
            last = s
        else:
            break
    return last


def _lookup_rate_by_date(exchange_rate_df: pd.DataFrame, date: pd.Timestamp) -> float:
    """거래일 환율을 조회한다. 정확히 없으면 직전 값(ffill)을 사용."""
    if date in exchange_rate_df.index:
        return float(exchange_rate_df.loc[date, "Close"])
    # ffill: 해당 날짜 이전 가장 가까운 값
    mask = exchange_rate_df.index <= date
    if mask.any():
        return float(exchange_rate_df.loc[mask, "Close"].iloc[-1])
    return float(exchange_rate_df["Close"].iloc[0])


def run_dual_market_backtest(
    params: BacktestParams,
    kospi_price_data: dict[str, pd.DataFrame],
    nasdaq_price_data: dict[str, pd.DataFrame],
    kospi_listing_df: pd.DataFrame | None,
    nasdaq_listing_df: pd.DataFrame | None,
    kospi_df: pd.DataFrame | None,
    nasdaq_df: pd.DataFrame | None,
    exchange_rate_df: pd.DataFrame,
    progress_callback=None,
) -> BacktestResult:
    """KOSPI + NASDAQ 이중 시장 백테스트를 실행한다.

    초기 자본을 kospi_ratio 비율로 분할하고, 미국 몫은 시작일 환율로
    USD 환전 후 각 시장을 독립적으로 시뮬레이션한다.
    합산 시 일별 환율로 NASDAQ 포트폴리오를 KRW 환산한다.
    """
    ratio = params.kospi_ratio / 100.0
    kospi_cash = params.initial_cash * ratio
    nasdaq_cash_krw = params.initial_cash * (1 - ratio)

    start_rate = _lookup_rate_by_date(
        exchange_rate_df,
        pd.Timestamp(params.start_date),
    )
    nasdaq_cash_usd = nasdaq_cash_krw / start_rate if start_rate > 0 else 0.0

    # KOSPI 백테스트
    kospi_params = BacktestParams(
        initial_cash=kospi_cash,
        start_date=params.start_date,
        end_date=params.end_date,
        fee_rate=params.fee_rate,
        n_rise_days=params.n_rise_days,
        m_fall_days=params.m_fall_days,
        y_emergency_pct=params.y_emergency_pct,
        max_buy_amount=params.max_buy_amount,
        min_balance=params.min_balance,
        sort_method=params.sort_method,
        kospi_ratio=100,
    )

    kospi_result = run_backtest(
        kospi_params, kospi_price_data, kospi_listing_df, kospi_df,
        progress_callback=lambda cur, tot: progress_callback(cur, tot * 2) if progress_callback else None,
    )

    # KOSPI 거래에 market 태그
    for t in kospi_result.trades:
        t.market = "KOSPI"

    # NASDAQ 백테스트 (USD 기준)
    nasdaq_max_buy = params.max_buy_amount / start_rate if start_rate > 0 else 0.0
    nasdaq_min_balance = params.min_balance / start_rate if start_rate > 0 else 0.0

    nasdaq_params = BacktestParams(
        initial_cash=nasdaq_cash_usd,
        start_date=params.start_date,
        end_date=params.end_date,
        fee_rate=params.fee_rate,
        n_rise_days=params.n_rise_days,
        m_fall_days=params.m_fall_days,
        y_emergency_pct=params.y_emergency_pct,
        max_buy_amount=nasdaq_max_buy,
        min_balance=nasdaq_min_balance,
        sort_method=params.sort_method,
        kospi_ratio=0,
    )

    nasdaq_result = run_backtest(
        nasdaq_params, nasdaq_price_data, nasdaq_listing_df, nasdaq_df,
        progress_callback=lambda cur, tot: progress_callback(tot + cur, tot * 2) if progress_callback else None,
    )

    # NASDAQ 거래에 market 태그
    for t in nasdaq_result.trades:
        t.market = "NASDAQ"

    # 일별 합산: 모든 날짜 유니온 구하기
    all_date_strs: set[str] = set()
    for s in kospi_result.daily_snapshots:
        all_date_strs.add(s.date)
    for s in nasdaq_result.daily_snapshots:
        all_date_strs.add(s.date)
    sorted_dates = sorted(all_date_strs)

    combined_snapshots: list[DailySnapshot] = []
    for date_str in sorted_dates:
        k_snap = _lookup_by_date(kospi_result.daily_snapshots, date_str)
        n_snap = _lookup_by_date(nasdaq_result.daily_snapshots, date_str)
        rate = _lookup_rate_by_date(exchange_rate_df, pd.Timestamp(date_str))

        k_cash = k_snap.cash if k_snap else 0.0
        k_stock = k_snap.stock_value if k_snap else 0.0
        n_cash = (n_snap.cash if n_snap else 0.0) * rate
        n_stock = (n_snap.stock_value if n_snap else 0.0) * rate

        combined_cash = k_cash + n_cash
        combined_stock = k_stock + n_stock
        combined_snapshots.append(DailySnapshot(
            date=date_str,
            cash=combined_cash,
            stock_value=combined_stock,
            total_value=combined_cash + combined_stock,
        ))

    # 합산 거래 및 수수료 (NASDAQ 수수료는 환율 반영)
    all_trades = kospi_result.trades + nasdaq_result.trades
    all_trades.sort(key=lambda t: t.date)

    # 합산 메트릭 계산
    metrics = _compute_metrics_from_snapshots(
        combined_snapshots, all_trades, params.initial_cash,
    )
    # 수수료는 KRW 기준으로 합산 (NASDAQ 수수료 * 시작 환율)
    kospi_fee = sum(t.fee for t in kospi_result.trades)
    nasdaq_fee = sum(t.fee for t in nasdaq_result.trades) * start_rate
    metrics["total_fee"] = round(kospi_fee + nasdaq_fee, 0)

    return BacktestResult(
        daily_snapshots=combined_snapshots,
        trades=all_trades,
        kospi_index=kospi_df,
        nasdaq_index=nasdaq_df,
        exchange_rate_df=exchange_rate_df,
        initial_exchange_rate=start_rate,
        kospi_snapshots=kospi_result.daily_snapshots,
        nasdaq_snapshots=nasdaq_result.daily_snapshots,
        total_trades=len(all_trades),
        **metrics,
    )
