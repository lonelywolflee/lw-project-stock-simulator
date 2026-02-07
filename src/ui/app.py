"""Streamlit 메인 진입점 - KOSPI 알고리즘 거래 시뮬레이터."""

import streamlit as st

from src.data.fetcher import fetch_all_prices, fetch_kospi_index, fetch_stock_listing
from src.engine.backtest import run_backtest
from src.ui.charts import render_asset_chart, render_comparison_chart
from src.ui.sidebar import render_sidebar
from src.ui.tables import render_metrics, render_trade_table

st.set_page_config(
    page_title="KOSPI 알고리즘 거래 시뮬레이터",
    page_icon="📈",
    layout="wide",
)

st.title("KOSPI 알고리즘 거래 시뮬레이터")
st.caption("FinanceDataReader 기반 백테스팅 엔진")

params = render_sidebar()

if params is not None:
    with st.spinner("데이터를 로딩하고 있습니다..."):
        # 종목 목록 로드
        status_text = st.empty()
        status_text.text("KOSPI 종목 목록을 불러오는 중...")
        listing_df = fetch_stock_listing()

        if listing_df is None or listing_df.empty:
            st.error("종목 목록을 불러올 수 없습니다. 네트워크 연결을 확인해주세요.")
            st.stop()

        # 종목 코드 추출
        codes = listing_df["Code"].tolist()

        # 가격 데이터 로드
        progress_bar = st.progress(0, text="주가 데이터 수집 중...")

        def update_progress(current: int, total: int):
            pct = current / total
            progress_bar.progress(pct, text=f"주가 데이터 수집 중... ({current}/{total})")

        price_data = fetch_all_prices(
            codes, params.start_date, params.end_date,
            progress_callback=update_progress,
        )
        progress_bar.empty()

        if not price_data:
            st.error("가격 데이터를 불러올 수 없습니다.")
            st.stop()

        status_text.text("KOSPI 지수 데이터를 불러오는 중...")
        kospi_df = fetch_kospi_index(params.start_date, params.end_date)

        status_text.empty()

    # 백테스트 실행
    with st.spinner("백테스트를 실행하고 있습니다..."):
        bt_progress = st.progress(0, text="백테스트 실행 중...")

        def bt_update(current: int, total: int):
            pct = current / total
            bt_progress.progress(pct, text=f"백테스트 실행 중... ({current}/{total}일)")

        result = run_backtest(
            params=params,
            price_data=price_data,
            listing_df=listing_df,
            kospi_df=kospi_df,
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

    tab1, tab2, tab3 = st.tabs(["자산 추이", "KOSPI 비교", "거래 내역"])

    with tab1:
        render_asset_chart(result)
    with tab2:
        render_comparison_chart(result)
    with tab3:
        render_trade_table(result)
else:
    st.info("왼쪽 사이드바에서 파라미터를 설정하고 'Run Simulation' 버튼을 클릭하세요.")
