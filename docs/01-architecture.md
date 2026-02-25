# 아키텍처

## 개요

KOSPI + NASDAQ 이중 시장 알고리즘 거래 시뮬레이터. FinanceDataReader로 과거 데이터를 수집하고, 시그널 기반 백테스트 엔진으로 매매 전략을 시뮬레이션한 뒤, React 대시보드로 결과를 시각화한다.

## 핵심 흐름

```
React Form → POST /api/backtests/run → 데이터 수집 + 엔진 실행 → BacktestResult 즉시 반환
```

동기 API로 동작하며, 별도의 큐나 폴링 없이 HTTP 응답으로 결과를 직접 반환한다.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| **Backend** | Django 5.x + django-ninja (REST API), 외부 DB/큐 없음 (in-memory SQLite) |
| **Frontend** | React 19 + TypeScript + Vite, shadcn/ui + Tailwind CSS v4, TanStack Query v5, Recharts |
| **데이터** | FinanceDataReader (주가/지수/환율), Pandas/NumPy |
| **패키지** | uv (backend), npm (frontend) |

## 프로젝트 구조

```
backend/
├── config/          → Django 설정 (settings/base.py, urls)
├── apps/
│   ├── backtests/   → 백테스트 API, 스키마, 직렬화
│   └── market_data/ → 종목 데이터 API
├── core/
│   ├── engine/      → 시그널 감지, 포트폴리오 관리, 백테스트 엔진 (순수 로직)
│   └── data/        → FinanceDataReader 래퍼 + Parquet 캐시
└── tests/           → pytest 기반 단위/통합 테스트

frontend/
├── src/
│   ├── api/         → Axios 클라이언트 + TypeScript 타입
│   ├── hooks/       → TanStack Query 커스텀 훅
│   ├── components/  → 재사용 UI 컴포넌트 (폼, 차트, 테이블, 메트릭)
│   ├── features/    → 페이지 단위 컴포넌트 (BacktestDashboard)
│   └── utils/       → 포매터, 색상 유틸리티
└── ...
```

## 레이어 간 의존 관계

```
frontend (React SPA)
    ↓ HTTP (axios, timeout 600s)
apps/ (Django-ninja API)
    ↓ 함수 호출
core/engine/ (순수 로직, 외부 I/O 없음)
core/data/   (FinanceDataReader + Parquet 캐시)
```

- `core/engine/`은 Django에 의존하지 않는 순수 Python 모듈이다
- `core/data/`는 외부 API(FinanceDataReader)와의 유일한 I/O 경계이다
- `apps/`는 Django-ninja 라우터로, `core/`의 함수를 호출하여 결과를 직렬화한다

## 주요 파일

| 파일 | 역할 |
|------|------|
| `backend/config/urls.py` | API 라우팅 진입점 (NinjaAPI 마운트) |
| `backend/apps/backtests/api.py` | 백테스트 동기 실행 엔드포인트 |
| `backend/apps/backtests/schemas.py` | Pydantic 요청/응답 스키마 (→ `frontend/src/api/types.ts`와 1:1) |
| `backend/apps/backtests/serializers.py` | BacktestResult → JSON 직렬화 |
| `backend/core/engine/backtest.py` | 백테스트 엔진 코어 (`run_backtest`, `run_dual_market_backtest`) |
| `frontend/src/features/backtest/BacktestDashboard.tsx` | 메인 페이지 컴포넌트 |
| `frontend/src/api/client.ts` | API 호출 함수 (Backend 연동 지점) |

## Backend 모듈 API

### `core/engine/` — 백테스트 엔진 (순수 로직)

**설계 원칙**
- 시그널은 사전 계산: `signals.py`의 함수들은 `pd.Series → pd.Series` 순수 함수. 백테스트 루프 진입 전에 모든 종목의 시그널을 한 번에 계산
- `run_backtest()`는 시장에 무관한 순수 시뮬레이션 함수. `run_dual_market_backtest()`가 자본 분할 → 독립 실행 → 환율 기반 합산을 오케스트레이팅

**`signals.py`** — 매수/매도 시그널 감지
- `detect_consecutive_rises(close_series, n)` → n일 연속 종가 상승 감지
- `detect_consecutive_falls(close_series, m)` → m일 연속 종가 하락 감지
- `detect_emergency_sell(close_series, y_pct)` → 당일 y% 이상 급락 감지

**`portfolio.py`** — 포트폴리오 상태 관리
- `Trade` / `Holding` / `DailySnapshot` / `Portfolio` 데이터 클래스
- `Portfolio.buy(date, code, name, price, max_amount, min_balance)` → 매수
- `Portfolio.sell_all(date, code, name, price)` → 전량 매도
- `Portfolio.snapshot(date, prices)` → 일별 스냅샷 기록

**`backtest.py`** — 백테스트 코어 엔진
- `BacktestParams` / `BacktestResult` 데이터 클래스
- `run_backtest(params, price_data, listing_df, kospi_df)` → 단일 시장 시뮬레이션
- `run_dual_market_backtest(...)` → KOSPI + NASDAQ 이중 시장 시뮬레이션

### `core/data/` — 데이터 수집 + 캐시

**`fetcher.py`** — FinanceDataReader 래퍼
- `_retry(func, *args, retries, **kwargs)`: 지수 백오프 재시도 (최대 3회, `RETRY_BASE_DELAY * 2^attempt`)
- `fetch_stock_listing(market)`: 상장 종목 목록 (`"KOSPI"` 또는 `"NASDAQ"`)
- `fetch_price_data(code, start, end)`: 개별 종목 일별 OHLCV (캐시 우선)
- `fetch_all_prices(codes, start, end, progress_callback)`: 여러 종목 순차 수집 → `dict[str, pd.DataFrame]`
- `fetch_kospi_index(start, end)`, `fetch_nasdaq_index(start, end)`, `fetch_exchange_rate(start, end)`

**`cache.py`** — Parquet 파일 기반 로컬 캐시 (`.cache/` 디렉토리)
- `get_cache_path(code, start, end)` → `{code}_{start}_{end}.parquet`
- `load_from_cache(code, start, end)` → 캐시 hit 시 DataFrame, miss 시 `None`
- `save_to_cache(code, start, end, df)` → Parquet 저장
- 캐시 키 = 종목코드 + 기간 (동일 종목이라도 기간 다르면 별도 캐시)

**가격 데이터 형식**: `dict[str, pd.DataFrame]` — 종목코드 → OHLCV DataFrame (DatetimeIndex)

## Frontend 모듈 API

**`api/`** — Axios 클라이언트
- `types.ts`: 백엔드 Pydantic 스키마 1:1 매핑 TypeScript 인터페이스
- `client.ts`: Axios 인스턴스 (`baseURL="/api"`, `timeout=600s`) + `runBacktest()` 단일 함수

**`hooks/`** — TanStack Query 커스텀 훅
- `useBacktest.ts`: `useRunBacktest()` — `useMutation`으로 동기 백테스트 실행

**`components/`** — 재사용 UI 컴포넌트
- `forms/BacktestForm.tsx`: React Hook Form + Zod 유효성 검증, 4개 카드 섹션 (기본 설정, 시장 비율, 전략 설정, 자금 설정)
- `charts/AssetChart.tsx`: Recharts AreaChart — 현금/주식평가액 스택 + 총자산 Line 오버레이
- `charts/ComparisonChart.tsx`: Recharts LineChart — 포트폴리오 vs KOSPI/NASDAQ 수익률 비교 (Base=100)
- `metrics/MetricsCards.tsx`: 5개 지표 카드 (수익률, MDD, 거래수, 승률, 수수료)
- `tables/TradeTable.tsx`: shadcn Table — 9열 거래내역 (시장별 KRW/USD 통화 포맷)

**`features/`** — 페이지 단위 컴포넌트
- `backtest/BacktestDashboard.tsx`: 메인 페이지 — aside(폼) + main(로딩/결과/빈 상태) 그리드 레이아웃
- `backtest/BacktestResults.tsx`: 결과 컨테이너 — MetricsCards + Tabs (자산 추이, 벤치마크 비교, 거래 내역)

**`utils/`** — 유틸리티
- `formatters.ts`: 한국 금융 포매터 (`formatKRW`, `formatUSD`, `formatPercent`, `formatDate` 등)
- `colors.ts`: 금융 색상 상수 (상승=빨강, 하락=파랑) + `getProfitColor` 유틸리티
