# Architecture

## Overview

프로젝트의 정식 이름은 "Stock Operating System"이다. `KOSPI` 와 `S&P 500` 에 포함된 기업을 대상으로 추세 투자법을 기반으로 상승시 매수, 하락시 매도하는 전략을 시뮬레이션하고, 이를 통해 얻은 매직넘버를 이용하여 실제 거래를 실행하는 프로젝트이다. `FinanceDataReader`로 과거 데이터를 수집하고, 시그널 기반 백테스트 엔진으로 매매 전략을 시뮬레이션한 뒤, React 대시보드로 결과를 시각화한다. 실제 거래는 `한국투자증권 API`를 이용하여 실행하며, 이를 제어하기 위한 서비스의 계정 관리와 거래 종목 관리는 `SQLite`를 이용한다.

## Design Principles

1. **모듈화 · 재사용** — 구조적으로 작성하고 재사용 가능하게 모듈화하여 중복을 없앤다.
2. **Functional Programming** — 가독성과 테스트 용이성을 최우선 가치로 삼는다.
3. **비동기 + 친절한 UX** — 오래 걸리는 작업은 비동기 통신을 사용하고, 진행 상태를 사용자가 인지할 수 있는 UX를 제공한다.
4. **Zero Trust 보안** — 데이터 위변조를 철저히 검수하며, 로그인을 제외한 모든 화면은 인증/인가 확인 후 진행한다.
5. **레이어 분리** — 목적이 명확하고 경계가 분명한 레이어를 사용하되, 언어 및 서비스 타입(FE, BE, Batch 등)에 맞는 best practice를 따른다.
6. **최신 안정 스택** — 2026년 기준 최신의 가장 안정된 기술 스택과 구현 패턴을 채택한다.
7. **보수적 예외 처리** — 중복 처리 없이, 레이어별로 자신에게 필요한 예외 처리만 담당한다.

## Core Features & Workflows

### 핵심 기능

| 기능 | 설명 |
|------|------|
| 백테스트 시뮬레이션 | 파라미터 기반 추세 매매 전략 백테스트 실행 |
| 결과 시각화 | 자산 변동 차트, 벤치마크 비교, 거래 내역 테이블, 핵심 지표 카드 (수익률 · MDD · 승률 · 수수료) |
| 시장 데이터 수집 | KOSPI · NASDAQ 종목의 과거 OHLCV 데이터 수집 및 Parquet 캐싱 |
| 종목 목록 조회 | KOSPI · NASDAQ 상장 종목 목록 조회 API (시가총액 포함) |
| 이중 시장 지원 | KOSPI/NASDAQ 비율 분할 투자 + USD/KRW 환율 환산 |
| 실거래 연동 | 한국투자증권 API를 통한 실제 매매 실행 (예정) |

### 주요 워크플로우

```
사용자: 파라미터 입력 (기간, 자금, 전략 설정)
  → Frontend: 폼 검증 → API 호출
    → Backend: 시장 데이터 수집/캐싱
      → Engine: 시그널 사전 계산 → 일별 매매 시뮬레이션 (SELL → BUY → SNAPSHOT)
               (이중 시장 시: 자본 분할 → KOSPI·NASDAQ 독립 시뮬레이션 → 환율 환산 합산)
    → Backend: 지표 계산 (수익률, MDD, 승률, 수수료) → 결과 응답
  → Frontend: 차트 · 지표 · 거래 내역 렌더링
```

매매 알고리즘 상세는 [algorithm.md](./05-algorithm.md)를 참고한다.

## Technology Stack

### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.12+ | 런타임 |
| Django | 5.1 | 웹 프레임워크 |
| django-ninja | 1.3 | REST API (FastAPI 스타일) |
| django-cors-headers | 4.4 | CORS 정책 관리 |
| FinanceDataReader | latest | 주가 · 시가총액 데이터 수집 |
| Pandas / NumPy | latest | 데이터 분석, 시뮬레이션 연산 |
| PyArrow | latest | 고속 데이터 캐싱 (Parquet) |
| python-dotenv | 1.0 | 환경 변수 관리 |
| uv | latest | 패키지 · 프로젝트 관리 |

### Frontend

| 기술 | 버전 | 용도 |
|------|------|------|
| React | 19 | UI 라이브러리 |
| TypeScript | 5.9 | 타입 안전성 |
| Vite | 7 | 빌드 · 개발 서버 |
| TailwindCSS | 4 | 유틸리티 기반 스타일링 |
| shadcn/ui + Radix UI | latest | UI 컴포넌트 |
| Recharts | 3 | 차트 시각화 |
| Lightweight Charts | 5 | 금융 차트 시각화 (캔들스틱) |
| TanStack Query | 5 | 서버 상태 관리 |
| Zustand | 5 | 클라이언트 상태 관리 |
| React Hook Form + Zod | 7 / 4 | 폼 관리 · 유효성 검증 |
| Axios | 1 | HTTP 클라이언트 |

### Infrastructure

| 기술 | 용도 |
|------|------|
| Docker Compose | 로컬 개발 환경 오케스트레이션 |
| SQLite | 계정 관리, 거래 종목 관리 (예정) |

## Data Flow

### 백테스트 실행 흐름

```
┌──────────────────┐    POST /api/backtests/run    ┌──────────────────┐
│  Frontend        │ ────────────────────────────→  │  Backend API     │
│                  │                                │                  │
│  useRunBacktest()│                                │  api.py: run()   │
│  → runBacktest() │                                │                  │
│  (Axios POST)    │  ←──────────────────────────── │  serialize_result│
│                  │    JSON: BacktestResultSchema   │  ()              │
└──────────────────┘                                └────────┬─────────┘
                                                             │
                                          ┌──────────────────┼──────────────────┐
                                          │ 1. 데이터 로딩    │                  │
                                          ▼                  ▼                  ▼
                                ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
                                │ fetch_stock  │  │ fetch_all    │  │ fetch_kospi_index │
                                │ _listing()   │  │ _prices()    │  │ fetch_nasdaq_index│
                                │ 종목 목록     │  │ 전종목 가격   │  │ fetch_exchange    │
                                │              │  │              │  │ _rate()           │
                                └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
                                       │                 │                   │
                                       │                 ▼                   │
                                       │       ┌──────────────────┐          │
                                       │       │ fetch_price_data │          │
                                       │       │ (종목별 호출)     │          │
                                       │       └────────┬─────────┘          │
                                       │                │                    │
                                       ▼                ▼                    ▼
                                ┌───────────────────────────────────────────────┐
                                │              cache.py                         │
                                │  load_from_cache() → 히트 시 Parquet 반환     │
                                │  미스 시 → FinanceDataReader → save_to_cache()│
                                └───────────────────────────────────────────────┘
                                                             │
                                          ┌──────────────────┘
                                          │ 2. 백테스트 실행
                                          ▼
                                ┌──────────────────────────────────────┐
                                │  backtest.py                         │
                                │                                      │
                                │  run_backtest()                      │
                                │  또는 run_dual_market_backtest()     │
                                └──────────────────┬───────────────────┘
                                                   │
                                    ┌──────────────┼──────────────┐
                                    ▼              ▼              ▼
                          ┌──────────────┐  ┌───────────┐  ┌──────────────┐
                          │ signals.py   │  │ 일별 루프  │  │ portfolio.py │
                          │              │  │            │  │              │
                          │ _precompute  │  │ SELL Phase │  │ Portfolio    │
                          │ _signals()   │  │ BUY Phase  │  │ .buy()      │
                          │              │  │ SNAPSHOT   │  │ .sell_all() │
                          │ • 연속상승   │  │            │  │ .snapshot() │
                          │ • 연속하락   │  │            │  │              │
                          │ • 긴급매도   │  │            │  │              │
                          └──────────────┘  └───────────┘  └──────────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │ _compute_metrics │
                                          │ 수익률·MDD·승률  │
                                          │ ·수수료 계산      │
                                          └──────────────────┘
```

### 함수 호출 체인

**단일 시장 (KOSPI 100% 또는 NASDAQ 100%)**

```
api.run()
├── fetch_stock_listing(market)
├── fetch_all_prices(codes, start, end)
│   └── fetch_price_data(code, start, end)  # 종목별
│       ├── load_from_cache(code, start, end)
│       └── fdr.DataReader() → save_to_cache()
├── fetch_kospi_index() / fetch_nasdaq_index()
│   ├── load_from_cache()
│   └── fdr.DataReader() → save_to_cache()
├── run_backtest(params, price_data, listing_df, index_df)
│   ├── _precompute_signals(price_data, n, m, y)
│   │   ├── detect_consecutive_rises(close, n)
│   │   ├── detect_consecutive_falls(close, m)
│   │   └── detect_emergency_sell(close, y)
│   ├── 일별 루프 (trading_dates)
│   │   ├── SELL: portfolio.sell_all()
│   │   ├── BUY:  portfolio.buy()
│   │   └── SNAP: portfolio.snapshot()
│   └── _compute_metrics(portfolio, initial_cash)
└── serialize_result(result) → JSON 응답
```

**이중 시장 (KOSPI + NASDAQ 비율 분할)**

```
api.run()
├── fetch_stock_listing("KOSPI") + fetch_stock_listing("NASDAQ")
├── fetch_all_prices(kospi_codes) + fetch_all_prices(nasdaq_codes)
├── fetch_kospi_index() + fetch_nasdaq_index() + fetch_exchange_rate()
├── run_dual_market_backtest(...)
│   ├── 자본 분할: kospi_cash = initial × ratio, nasdaq_cash_usd = (initial × (1-ratio)) / 환율
│   ├── run_backtest(kospi_params, kospi_prices, ...)   # KRW 기준
│   ├── run_backtest(nasdaq_params, nasdaq_prices, ...)  # USD 기준
│   ├── 일별 합산: NASDAQ 스냅샷 × 당일 환율 → KRW 환산 후 KOSPI와 합산
│   └── _compute_metrics_from_snapshots(combined, all_trades, initial_cash)
└── serialize_result(result) → JSON 응답
```

### 데이터 캐싱

`fetcher.py`의 모든 데이터 수집 함수(`fetch_price_data`, `fetch_kospi_index`, `fetch_nasdaq_index`, `fetch_exchange_rate`)는 `cache.py`를 통해 동일한 캐싱 전략을 사용한다.

- **캐시 키**: `{종목코드}_{시작일}_{종료일}` (예: `005930_2024-01-01_2024-12-31.parquet`)
- **저장 형식**: Apache Parquet (PyArrow)
- **저장 위치**: 프로젝트 루트의 `.cache/` 디렉토리
- **캐시 정책**: 동일 종목·동일 기간 요청 시 캐시 히트, 기간이 다르면 미스 (기간 단위 exact match)
- **네트워크 장애 대응**: `_retry()` 함수가 지수 백오프(1s → 2s → 4s)로 최대 3회 재시도

## Project Structure




## Modules

### Backend Modules


### Frontend Modules

