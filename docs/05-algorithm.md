# 매매 알고리즘 명세

이 문서는 백테스트 엔진의 비즈니스 로직을 설명한다. 모듈별 API 시그니처는 [`.claude/rules/engine.md`](../.claude/rules/engine.md)를 참고한다.

## 시뮬레이션 흐름

```
입력 파라미터 → 데이터 수집 → 시그널 사전 계산 → 일별 루프 (SELL → BUY → SNAPSHOT) → 지표 계산 → 결과 반환
```

## 데이터 수집

FinanceDataReader를 통해 다음 데이터를 수집한다:

| 데이터 | 소스 | 용도 |
|--------|------|------|
| 종목별 일별 OHLCV | `fetch_all_prices()` | 시그널 계산 + 매매 가격 |
| 상장 종목 목록 | `fetch_stock_listing()` | 시총 정렬, 종목명 매핑 |
| KOSPI 지수 (KS11) | `fetch_kospi_index()` | 벤치마크 비교 |
| NASDAQ Composite (IXIC) | `fetch_nasdaq_index()` | 벤치마크 비교 |
| USD/KRW 환율 | `fetch_exchange_rate()` | 이중 시장 합산 |

## 시그널 사전 계산

일별 루프 진입 전, 모든 종목의 시그널을 한 번에 계산한다:

| 시그널 | 함수 | 입력 | 출력 |
|--------|------|------|------|
| 매수 | `detect_consecutive_rises(close, n)` | 종가 Series, 연속 상승 일수 | Boolean Series |
| 매도 (추세 하락) | `detect_consecutive_falls(close, m)` | 종가 Series, 연속 하락 일수 | Boolean Series |
| 매도 (긴급 손절) | `detect_emergency_sell(close, y_pct)` | 종가 Series, 급락 비율(%) | Boolean Series |

## 일별 시뮬레이션 루프

매 거래일마다 다음 순서로 실행된다:

### 1단계: SELL (매도)

보유 종목을 순회하며 매도 시그널을 확인한다:

1. **추세 하락 매도**: m일 연속 하락 → 전량 매도
2. **긴급 손절**: 당일 y% 이상 급락 → 전량 매도
3. 매도 시 금액의 `fee_rate`%를 수수료로 차감

### 2단계: BUY (매수)

매수 시그널이 발생한 비보유 종목을 후보로 선정한다:

1. **후보 선정**: n일 연속 상승 + 미보유 종목
2. **정렬**: `sort_method`에 따라 시가총액 순 또는 n일간 수익률 순으로 정렬
3. **매수 실행**: 후보를 순서대로 종목당 최대 `max_buy_amount`만큼 매수
4. **중단 조건**: 매수 후 잔고가 `min_balance` 미만이면 해당일 추가 매수 중단
5. 매수 시 금액의 `fee_rate`%를 수수료로 차감

### 3단계: SNAPSHOT (기록)

현재 보유 종목의 시가 평가액을 계산하고, 일별 자산 현황(현금 + 주식 평가액 = 총자산)을 기록한다.

## 이중 시장 모델

`kospi_ratio`가 100 미만일 때 활성화된다:

1. **자본 분할**: 초기 자금을 `kospi_ratio : (100 - kospi_ratio)` 비율로 분할
2. **환전**: NASDAQ 몫을 시작일 USD/KRW 환율로 USD 환전
3. **독립 실행**: KOSPI, NASDAQ 각각 `run_backtest()`로 독립 시뮬레이션
4. **합산**: 일별 NASDAQ 자산을 해당일 환율로 KRW 환산 후 KOSPI 자산과 합산
5. **수수료**: NASDAQ 수수료는 시작일 환율로 KRW 환산하여 합산

## 입력 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `initial_cash` | float | (필수) | 초기 투자 자금 (KRW) |
| `start_date` | str | (필수) | 시뮬레이션 시작일 (YYYY-MM-DD) |
| `end_date` | str | (필수) | 시뮬레이션 종료일 (YYYY-MM-DD) |
| `fee_rate` | float | 0.015 | 매매 수수료율 (%) |
| `n_rise_days` | int | 3 | 매수 시그널: 연속 상승 일수 |
| `m_fall_days` | int | 3 | 매도 시그널: 연속 하락 일수 |
| `y_emergency_pct` | float | 5.0 | 긴급 매도: 당일 급락 비율 (%) |
| `max_buy_amount` | float | (필수) | 종목당 최대 매수 금액 |
| `min_balance` | float | (필수) | 매수 후 최소 잔고 |
| `sort_method` | str | "market_cap" | 매수 정렬 방식 ("market_cap" 또는 "return_rate") |
| `kospi_ratio` | int | 100 | KOSPI 투자 비율 (0~100, 나머지 NASDAQ) |

## 출력

| 필드 | 설명 |
|------|------|
| `daily_snapshots` | 일별 자산 현황 (date, cash, stock_value, total_value) |
| `trades` | 전체 거래 내역 (date, code, name, side, price, quantity, amount, fee, profit, market) |
| `kospi_index` / `nasdaq_index` | 벤치마크 지수 데이터 |
| `final_return_pct` | 최종 수익률 (%) |
| `mdd_pct` | 최대 낙폭 MDD (%) |
| `total_trades` | 총 거래 횟수 |
| `win_rate_pct` | 승률 (매도 거래 중 수익 비율, %) |
| `total_fee` | 총 수수료 (KRW) |
