"""Plotly 시각화 모듈 - 자산 차트, KOSPI 비교."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.engine.backtest import BacktestResult


def render_asset_chart(result: BacktestResult) -> None:
    """자산 추이 영역 차트를 렌더링한다 (현금 + 주식가치)."""
    if not result.daily_snapshots:
        st.warning("시뮬레이션 결과가 없습니다.")
        return

    dates = [s.date for s in result.daily_snapshots]
    cash = [s.cash for s in result.daily_snapshots]
    stock_value = [s.stock_value for s in result.daily_snapshots]
    total = [s.total_value for s in result.daily_snapshots]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=cash, name="현금",
        fill="tozeroy", mode="lines",
        line=dict(width=0.5, color="rgb(131, 165, 152)"),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=stock_value, name="주식 평가액",
        fill="tozeroy", mode="lines",
        line=dict(width=0.5, color="rgb(69, 133, 136)"),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=total, name="총 자산",
        mode="lines",
        line=dict(width=2, color="rgb(214, 93, 14)"),
    ))

    fig.update_layout(
        title="자산 추이",
        xaxis_title="날짜",
        yaxis_title="금액 (원)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_comparison_chart(result: BacktestResult) -> None:
    """포트폴리오 vs KOSPI 수익률 비교 차트를 렌더링한다 (base=100 정규화)."""
    if not result.daily_snapshots:
        st.warning("시뮬레이션 결과가 없습니다.")
        return

    dates = [s.date for s in result.daily_snapshots]
    total_values = [s.total_value for s in result.daily_snapshots]

    base = total_values[0] if total_values[0] != 0 else 1
    portfolio_normalized = [v / base * 100 for v in total_values]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=portfolio_normalized, name="포트폴리오",
        mode="lines",
        line=dict(width=2, color="rgb(214, 93, 14)"),
    ))

    if result.kospi_index is not None and not result.kospi_index.empty:
        kospi = result.kospi_index
        kospi_close = kospi["Close"]

        # 시뮬레이션 기간과 겹치는 날짜만 사용
        kospi_dates = [d.strftime("%Y-%m-%d") for d in kospi_close.index]
        kospi_base = kospi_close.iloc[0] if kospi_close.iloc[0] != 0 else 1
        kospi_normalized = (kospi_close / kospi_base * 100).tolist()

        fig.add_trace(go.Scatter(
            x=kospi_dates, y=kospi_normalized, name="KOSPI",
            mode="lines",
            line=dict(width=2, color="rgb(104, 157, 106)", dash="dash"),
        ))

    fig.add_hline(y=100, line_dash="dot", line_color="gray", opacity=0.5)

    fig.update_layout(
        title="수익률 비교 (Base = 100)",
        xaxis_title="날짜",
        yaxis_title="정규화 수익률",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    st.plotly_chart(fig, use_container_width=True)
