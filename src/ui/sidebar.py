"""사이드바 파라미터 컨트롤 모듈."""

from datetime import date, timedelta

import streamlit as st

from src.engine.backtest import BacktestParams


def render_sidebar() -> BacktestParams | None:
    """사이드바에 파라미터 입력 위젯을 렌더링하고 BacktestParams를 반환한다.

    "Run Simulation" 버튼이 눌리면 파라미터를 반환, 아니면 None.
    """
    st.sidebar.header("기본 설정")

    initial_cash = st.sidebar.number_input(
        "초기 자금 (원)", min_value=1_000_000, max_value=10_000_000_000,
        value=100_000_000, step=10_000_000, format="%d",
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "시작일", value=date.today() - timedelta(days=365),
        )
    with col2:
        end_date = st.date_input("종료일", value=date.today())

    fee_rate = st.sidebar.number_input(
        "매매 수수료 (%)", min_value=0.0, max_value=1.0,
        value=0.015, step=0.001, format="%.3f",
    )

    st.sidebar.header("시장 설정")

    kospi_ratio = st.sidebar.slider(
        "국내(KOSPI) 비율", min_value=0, max_value=100, value=50, step=5,
        help="나머지는 미국(NASDAQ)에 배분됩니다",
    )
    st.sidebar.caption(f"NASDAQ: {100 - kospi_ratio}%")

    st.sidebar.header("전략 설정")

    n_rise_days = st.sidebar.slider("연속 상승일 (n)", min_value=2, max_value=10, value=3)
    m_fall_days = st.sidebar.slider("연속 하락일 (m)", min_value=2, max_value=10, value=3)
    y_emergency_pct = st.sidebar.number_input(
        "긴급 매도 하락률 (%)", min_value=1.0, max_value=30.0,
        value=5.0, step=0.5,
    )

    st.sidebar.header("자금 설정")

    max_buy_amount = st.sidebar.number_input(
        "종목당 매수 상한 (원)", min_value=100_000, max_value=1_000_000_000,
        value=5_000_000, step=1_000_000, format="%d",
    )
    min_balance = st.sidebar.number_input(
        "매수 하한 잔고 (원)", min_value=0, max_value=1_000_000_000,
        value=1_000_000, step=1_000_000, format="%d",
    )

    sort_method = st.sidebar.radio(
        "정렬 방식",
        options=["market_cap", "return_rate"],
        format_func=lambda x: "시가총액 순" if x == "market_cap" else "수익률 순",
    )

    st.sidebar.divider()

    if st.sidebar.button("Run Simulation", type="primary", use_container_width=True):
        return BacktestParams(
            initial_cash=float(initial_cash),
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            fee_rate=float(fee_rate),
            n_rise_days=int(n_rise_days),
            m_fall_days=int(m_fall_days),
            y_emergency_pct=float(y_emergency_pct),
            max_buy_amount=float(max_buy_amount),
            min_balance=float(min_balance),
            sort_method=sort_method,
            kospi_ratio=int(kospi_ratio),
        )

    return None
