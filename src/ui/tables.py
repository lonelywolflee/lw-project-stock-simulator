"""지표 카드 및 거래내역 테이블 모듈."""

import pandas as pd
import streamlit as st

from src.engine.backtest import BacktestResult


def render_metrics(result: BacktestResult) -> None:
    """핵심 지표를 st.metric 카드로 렌더링한다."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="최종 수익률",
            value=f"{result.final_return_pct:+.2f}%",
        )
    with col2:
        st.metric(
            label="MDD",
            value=f"{result.mdd_pct:.2f}%",
        )
    with col3:
        st.metric(
            label="총 거래수",
            value=f"{result.total_trades}",
        )
    with col4:
        st.metric(
            label="승률",
            value=f"{result.win_rate_pct:.1f}%",
        )
    with col5:
        st.metric(
            label="총 수수료",
            value=f"{result.total_fee:,.0f}원",
        )


def render_trade_table(result: BacktestResult) -> None:
    """거래 내역을 스크롤 가능한 테이블로 렌더링한다."""
    if not result.trades:
        st.info("거래 내역이 없습니다.")
        return

    records = []
    for t in result.trades:
        is_nasdaq = t.market == "NASDAQ"
        currency_fmt = "${:,.2f}" if is_nasdaq else "{:,.0f}"
        records.append({
            "시장": t.market,
            "날짜": t.date,
            "종목코드": t.code,
            "종목명": t.name,
            "구분": t.side,
            "단가": currency_fmt.format(t.price),
            "수량": t.quantity,
            "금액": currency_fmt.format(t.amount),
            "수수료": currency_fmt.format(t.fee),
            "실현손익": currency_fmt.format(t.profit) if t.side == "SELL" else "-",
        })

    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True, height=400)
