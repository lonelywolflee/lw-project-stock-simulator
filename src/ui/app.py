"""Streamlit 메인 진입점 - 알고리즘 거래 시뮬레이터."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src.data.fetcher import (
    fetch_all_prices,
    fetch_exchange_rate,
    fetch_kospi_index,
    fetch_nasdaq_index,
    fetch_stock_listing,
)
from src.engine.backtest import run_backtest, run_dual_market_backtest
from src.ui.charts import render_asset_chart, render_comparison_chart
from src.ui.sidebar import render_sidebar
from src.ui.tables import render_metrics, render_trade_table

st.set_page_config(
    page_title="알고리즘 거래 시뮬레이터",
    page_icon="📈",
    layout="wide",
)

st.title("알고리즘 거래 시뮬레이터")
st.caption("FinanceDataReader 기반 백테스팅 엔진 (KOSPI + NASDAQ)")

params = render_sidebar()

if params is not None:
    with st.spinner("데이터를 로딩하고 있습니다..."):
        status_text = st.empty()

        # KOSPI 종목 목록
        status_text.text("KOSPI 종목 목록을 불러오는 중...")
        kospi_listing_df = fetch_stock_listing("KOSPI")

        if kospi_listing_df is None or kospi_listing_df.empty:
            st.error("KOSPI 종목 목록을 불러올 수 없습니다. 네트워크 연결을 확인해주세요.")
            st.stop()

        kospi_codes = kospi_listing_df["Code"].tolist()

        # NASDAQ 종목 목록 (필요한 경우만)
        nasdaq_listing_df = None
        nasdaq_codes = []
        if params.kospi_ratio < 100:
            status_text.text("NASDAQ 종목 목록을 불러오는 중...")
            nasdaq_listing_df = fetch_stock_listing("NASDAQ")
            if nasdaq_listing_df is not None and not nasdaq_listing_df.empty:
                nasdaq_codes = nasdaq_listing_df["Symbol"].tolist()
            else:
                st.error("NASDAQ 종목 목록을 불러올 수 없습니다.")
                st.stop()

        # KOSPI 가격 데이터
        progress_bar = st.progress(0, text="KOSPI 주가 데이터 수집 중...")

        def update_kospi_progress(current: int, total: int):
            pct = current / total
            progress_bar.progress(pct, text=f"KOSPI 주가 데이터 수집 중... ({current}/{total})")

        kospi_price_data = fetch_all_prices(
            kospi_codes, params.start_date, params.end_date,
            progress_callback=update_kospi_progress if params.kospi_ratio > 0 else None,
        ) if params.kospi_ratio > 0 else {}
        progress_bar.empty()

        # NASDAQ 가격 데이터 (필요한 경우만)
        nasdaq_price_data: dict = {}
        if params.kospi_ratio < 100 and nasdaq_codes:
            progress_bar = st.progress(0, text="NASDAQ 주가 데이터 수집 중...")

            def update_nasdaq_progress(current: int, total: int):
                pct = current / total
                progress_bar.progress(pct, text=f"NASDAQ 주가 데이터 수집 중... ({current}/{total})")

            nasdaq_price_data = fetch_all_prices(
                nasdaq_codes, params.start_date, params.end_date,
                progress_callback=update_nasdaq_progress,
            )
            progress_bar.empty()

        # 지수 데이터
        status_text.text("지수 데이터를 불러오는 중...")
        kospi_df = fetch_kospi_index(params.start_date, params.end_date)

        nasdaq_df = None
        exchange_rate_df = None
        if params.kospi_ratio < 100:
            nasdaq_df = fetch_nasdaq_index(params.start_date, params.end_date)
            exchange_rate_df = fetch_exchange_rate(params.start_date, params.end_date)

        status_text.empty()

    # 백테스트 실행
    with st.spinner("백테스트를 실행하고 있습니다..."):
        bt_progress = st.progress(0, text="백테스트 실행 중...")

        def bt_update(current: int, total: int):
            pct = current / total
            bt_progress.progress(pct, text=f"백테스트 실행 중... ({current}/{total}일)")

        if params.kospi_ratio == 100:
            # KOSPI only 모드
            result = run_backtest(
                params=params,
                price_data=kospi_price_data,
                listing_df=kospi_listing_df,
                kospi_df=kospi_df,
                progress_callback=bt_update,
            )
        else:
            # 이중 시장 모드
            result = run_dual_market_backtest(
                params=params,
                kospi_price_data=kospi_price_data,
                nasdaq_price_data=nasdaq_price_data,
                kospi_listing_df=kospi_listing_df,
                nasdaq_listing_df=nasdaq_listing_df,
                kospi_df=kospi_df,
                nasdaq_df=nasdaq_df,
                exchange_rate_df=exchange_rate_df,
                progress_callback=bt_update,
            )
        bt_progress.empty()

    # 결과 저장
    st.session_state["result"] = result

# 결과 표시
if "result" in st.session_state:
    result = st.session_state["result"]

    st.header("시뮬레이션 결과")
    render_metrics(result)

    tab1, tab2, tab3 = st.tabs(["자산 추이", "벤치마크 비교", "거래 내역"])

    with tab1:
        render_asset_chart(result)
    with tab2:
        render_comparison_chart(result)
    with tab3:
        render_trade_table(result)
else:
    st.info("왼쪽 사이드바에서 파라미터를 설정하고 'Run Simulation' 버튼을 클릭하세요.")
