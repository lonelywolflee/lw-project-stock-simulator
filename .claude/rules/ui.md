# src/ui/ 레이어 개발 가이드

## 역할

Streamlit 프레젠테이션 — 사이드바 파라미터 입력, Plotly 차트 시각화, 지표/거래 테이블 표시.

## 실행

```bash
uv run streamlit run src/ui/app.py
```

## 모듈 구성

### `app.py` — 메인 진입점

데이터 로딩 → 백테스트 실행 → 결과 표시 오케스트레이션:
1. `render_sidebar()` → `BacktestParams` 반환 (버튼 미클릭 시 `None`)
2. `fetch_stock_listing()` → `fetch_all_prices()` → 지수/환율 데이터 수집
3. `kospi_ratio`에 따라 `run_backtest()` 또는 `run_dual_market_backtest()` 실행
4. `render_metrics()` + 탭 3개 (자산 추이, 벤치마크 비교, 거래 내역)

### `sidebar.py` — 파라미터 입력 컨트롤

- `render_sidebar()` → `BacktestParams | None`
- 설정 섹션: 기본 설정 (자금, 기간, 수수료), 시장 설정 (KOSPI/NASDAQ 비율), 전략 설정 (n, m, y), 자금 설정 (매수상한, 하한잔고, 정렬방식)

### `charts.py` — Plotly 시각화

- `render_asset_chart(result)`: 자산 추이 영역 차트 (현금 + 주식가치 + 총자산)
- `render_comparison_chart(result)`: 포트폴리오 vs KOSPI/NASDAQ 수익률 비교 (Base=100 정규화)

### `tables.py` — 지표 카드 및 거래내역 테이블

- `render_metrics(result)`: `st.metric` 카드 5개 (수익률, MDD, 거래수, 승률, 수수료)
- `render_trade_table(result)`: 거래내역 DataFrame 테이블 (시장별 통화 포맷 분기)
