# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# 1. Backend 환경 설정
cp backend/.env.example backend/.env  # 필요 시 값 수정
cd backend && uv sync

# 2. Frontend 설치
cd frontend && npm install

# 3. 실행 (터미널 2개)
cd backend && uv run python manage.py runserver  # :8000
cd frontend && npm run dev                        # :5173
```

## Commands

```bash
# Backend - Run all tests
cd backend && uv run pytest tests/ -v

# Backend - Run a single test file
cd backend && uv run pytest tests/test_backtest.py -v

# Backend - Run a specific test class or method
cd backend && uv run pytest tests/test_backtest.py::TestDualMarketBacktest::test_dual_market_capital_split -v

# Backend - Run Django dev server
cd backend && uv run python manage.py runserver

# Frontend - Dev server
cd frontend && npm run dev

# Frontend - Type check
cd frontend && npx tsc --noEmit

# Frontend - Build check
cd frontend && npx vite build

# Frontend - Lint
cd frontend && npm run lint

# Docker - 전체 스택 실행
docker compose up
```

## Architecture

KOSPI + NASDAQ 이중 시장 알고리즘 거래 시뮬레이터. Django-ninja REST API (동기) + React SPA 대시보드.

**핵심 흐름**: React Form → POST /api/backtests/run → 데이터 수집 + 엔진 실행 → BacktestResult 즉시 반환

### Project Structure

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

### Tech Stack

- **Backend**: Django 5.x + django-ninja (REST API), 외부 DB/큐 없음 (in-memory SQLite)
- **Frontend**: React 19 + TypeScript + Vite, shadcn/ui + Tailwind CSS v4, TanStack Query v5, Recharts

## Key Files

- `backend/config/urls.py` — API 라우팅 진입점 (NinjaAPI 마운트)
- `backend/apps/backtests/api.py` — 백테스트 동기 실행 엔드포인트
- `backend/apps/backtests/schemas.py` — Pydantic 요청/응답 스키마 (→ `frontend/src/api/types.ts`와 1:1)
- `backend/apps/backtests/serializers.py` — BacktestResult → JSON 직렬화
- `backend/core/engine/backtest.py` — 백테스트 엔진 코어 (`run_backtest`, `run_dual_market_backtest`)
- `frontend/src/features/backtest/BacktestDashboard.tsx` — 메인 페이지 컴포넌트
- `frontend/src/api/client.ts` — API 호출 함수 (Backend 연동 지점)

## Environment

- Backend 환경 변수: `backend/.env.example` 참조 → `backend/.env`로 복사 후 설정
- 외부 인프라 불필요 (Redis, PostgreSQL 등 없음)
- `DJANGO_SECRET_KEY`: 미설정 시 DEBUG 모드에서만 dev 키 사용, production에서는 필수

## Key Conventions

- **Engine 순수 로직**: `backend/core/engine/`은 외부 I/O 없는 순수 로직. Django 의존 금지
- **일별 루프 순서**: SELL → BUY → SNAPSHOT (매도 우선으로 현금 확보 후 매수)
- **한국 금융 컬러**: 상승=빨강(red), 하락=파랑(blue) — 미국 컨벤션과 반대
- **이중 시장**: NASDAQ 포트폴리오는 USD 기준 운영, 합산 시 일별 USD/KRW 환율로 KRW 환산
- **Backend import**: `core.engine.*`, `core.data.*` (NOT `src.engine.*`)
- **Root `pyproject.toml`**: 메타데이터만 포함, 의존성은 `backend/pyproject.toml`과 `frontend/package.json`에 각각 관리
- **동기 API**: 백테스트는 동기 실행 (POST → 결과 즉시 반환). axios timeout 600초

## Testing

- 테스트 위치: `backend/tests/` (import: `core.engine.*`)
- 테스트 데이터: `_make_price_df()`, `_make_listing()` 헬퍼로 합성 데이터 생성
- 테스트는 Django 미의존 — 순수 Python 테스트, `pytest`만으로 실행 (pytest-django 불필요)
- Frontend 테스트: 미구성 (추후 Vitest 도입 예정)

## Gotchas

- NASDAQ 종목 목록의 코드 컬럼은 `"Symbol"` (KOSPI는 `"Code"`) — 매핑 시 주의
- `backend/core/`는 Django app이 아님 — `INSTALLED_APPS`에 등록하지 않는다
- 대규모 백테스트(이중 시장, 장기간) 시 HTTP 요청이 수 분 소요될 수 있음 — Production 배포 시 gunicorn `--timeout 600` 필요
- `apps/*/models.py`와 `apps/*/admin.py`는 빈 파일 — DB 모델/Admin 미사용. 마이그레이션, `makemigrations` 불필요
- `frontend/src/stores/` 디렉토리 없음 — Zustand 제거됨. 클라이언트 상태는 TanStack Query mutation으로 대체


## Rules Structure

각 레이어의 상세 개발 가이드는 `.claude/rules/` 하위에 분리되어 있다:

| 파일 | 대상 레이어 | 주요 내용 |
|------|------------|-----------|
| `.claude/rules/data.md` | `backend/core/data/` | FinanceDataReader 래퍼, Parquet 캐시, 가격 데이터 형식 |
| `.claude/rules/engine.md` | `backend/core/engine/` | 시그널 사전 계산, 일별 루프 순서, 이중 시장 모델, 매매 알고리즘 |
| `.claude/rules/ui.md` | `frontend/src/` | React 컴포넌트, TanStack Query 훅, Recharts 차트, shadcn/ui |

## Commit Convention

커밋 타입: `docs:`, `feat:`, `refactor:`, `fix:` (한국어 메시지). `/commit` 커맨드 사용 시 자동으로 목적별 분리 커밋.

## Notes

- `PRD.md`는 v0.1.0 원본 기획서 (Streamlit 참조 포함). 역사적 기록으로 수정하지 않는다
- 의존성 변경 후 `uv sync` (backend) 또는 `npm install` (frontend)로 lock 파일 재생성 필요
