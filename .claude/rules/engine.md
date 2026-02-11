# src/engine/ 레이어 개발 가이드

## 역할

시그널 감지, 포트폴리오 관리, 백테스트 엔진. 순수 로직만 포함하며 외부 I/O 의존 없음.

## 핵심 설계 원칙

- **시그널은 사전 계산**: `signals.py`의 함수들은 `pd.Series → pd.Series` 순수 함수. 백테스트 루프 진입 전에 모든 종목의 시그널을 한 번에 계산
- **일별 루프 순서**: SELL → BUY → SNAPSHOT. 매도가 먼저 실행되어 확보된 현금으로 같은 날 매수 가능
- **이중 시장 모델**: `run_backtest()`는 시장에 무관한 순수 시뮬레이션 함수. `run_dual_market_backtest()`가 자본 분할 → 독립 실행 → 환율 기반 합산을 오케스트레이팅. NASDAQ 포트폴리오는 USD 기준으로 운영되며, 합산 시 일별 USD/KRW 환율로 KRW 환산

## 모듈 구성

### `signals.py` — 매수/매도 시그널 감지 (순수 함수)

- `detect_consecutive_rises(close_series, n)` → n일 연속 종가 상승 감지
- `detect_consecutive_falls(close_series, m)` → m일 연속 종가 하락 감지
- `detect_emergency_sell(close_series, y_pct)` → 당일 y% 이상 급락 감지

### `portfolio.py` — 포트폴리오 상태 관리

- `Trade`: 개별 거래 기록 (date, code, name, side, price, quantity, amount, fee, profit, market)
- `Holding`: 보유 종목 정보 (code, name, quantity, avg_price)
- `DailySnapshot`: 일별 자산 현황 (date, cash, stock_value, total_value)
- `Portfolio`: 포트폴리오 전체 상태
  - `buy(date, code, name, price, max_amount, min_balance)` → 매수
  - `sell_all(date, code, name, price)` → 전량 매도
  - `snapshot(date, prices)` → 일별 스냅샷 기록

### `backtest.py` — 백테스트 코어 엔진

- `BacktestParams`: 실행 파라미터 (초기자금, 기간, 수수료율, 시그널 일수, 자금 설정, 시장 비율)
- `BacktestResult`: 결과 (snapshots, trades, 지수, 메트릭)
- `run_backtest(params, price_data, listing_df, kospi_df)` → 단일 시장 시뮬레이션
- `run_dual_market_backtest(...)` → KOSPI + NASDAQ 이중 시장 시뮬레이션

## 매매 알고리즘 요약

| 단계 | 조건 | 동작 |
|------|------|------|
| 매수 | n일 연속 상승 | 시총/수익률 정렬 → 종목당 최대 `max_buy_amount` 매수, 잔고 `min_balance` 미만 시 중단 |
| 매도 | m일 연속 하락 | 전량 매도 |
| 긴급 손절 | 당일 y% 이상 급락 | 전량 매도 |
| 수수료 | 매수/매도 시 | 금액의 `fee_rate`% 차감 |
