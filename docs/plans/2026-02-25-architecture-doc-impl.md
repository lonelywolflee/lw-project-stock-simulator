# Architecture Document Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `docs/01-architecture.md`의 빈 섹션들을 설계안에 따라 완성한다.

**Architecture:** 기존 Overview는 유지하고, 7개 섹션을 순차적으로 작성한다. 각 섹션은 코드베이스의 실제 구조를 반영하며, 다른 docs 문서와의 경계를 명확히 지킨다.

**Tech Stack:** Markdown 문서 작성. 코드베이스 참조 필요.

**Reference:** 설계안 `docs/plans/2026-02-25-architecture-doc-design.md`

---

### Task 1: Design Principles 섹션 작성

**Files:**
- Modify: `docs/01-architecture.md:8-9`

**Step 1: Design Principles 내용 작성**

사용자가 정의한 7개 원칙을 번호 리스트로 정리한다. 각 원칙은 **굵은 키워드** + 한 줄 설명 형태.

```markdown
## Design Principles

1. **모듈화 · 재사용** — 구조적으로 작성하고 재사용 가능하게 모듈화하여 중복을 없앤다.
2. **Functional Programming** — 가독성과 테스트 용이성을 최우선 가치로 삼는다.
3. **비동기 + 친절한 UX** — 오래 걸리는 작업은 비동기 통신을 사용하고, 진행 상태를 사용자가 인지할 수 있는 UX를 제공한다.
4. **Zero Trust 보안** — 데이터 위변조를 철저히 검수하며, 로그인을 제외한 모든 화면은 인증/인가 확인 후 진행한다.
5. **레이어 분리** — 목적이 명확하고 경계가 분명한 레이어를 사용하되, 언어 및 서비스 타입(FE, BE, Batch 등)에 맞는 best practice를 따른다.
6. **최신 안정 스택** — 2026년 기준 최신의 가장 안정된 기술 스택과 구현 패턴을 채택한다.
7. **보수적 예외 처리** — 중복 처리 없이, 레이어별로 자신에게 필요한 예외 처리만 담당한다.
```

**Step 2: 커밋**

```bash
git add docs/01-architecture.md
git commit -m "docs: 아키텍처 문서 Design Principles 섹션 작성"
```

---

### Task 2: Core Features & Workflows 섹션 작성

**Files:**
- Modify: `docs/01-architecture.md:12-13`
- Reference: `docs/06-prd-v0.1.0.md` (기능 목록), `docs/05-algorithm.md` (알고리즘 상세)

**Step 1: 핵심 기능 리스트 및 워크플로우 작성**

시스템 수준의 기능 목록과 고수준 사용자 흐름도를 작성한다. 알고리즘 상세는 `05-algorithm.md` 링크로 위임.

참고할 코드:
- `backend/apps/backtests/api.py` — 백테스트 API 엔드포인트
- `backend/apps/market_data/api.py` — 시장 데이터 API
- `backend/core/engine/` — 백테스트 엔진
- `frontend/src/features/backtest/` — 대시보드 UI

```markdown
## Core Features & Workflows

### 핵심 기능

| 기능 | 설명 |
|------|------|
| 백테스트 시뮬레이션 | 파라미터 기반 추세 매매 전략 백테스트 실행 |
| 결과 시각화 | 자산 변동 차트, 벤치마크 비교, 거래 내역 테이블 |
| 시장 데이터 수집 | KOSPI · NASDAQ 종목의 과거 OHLCV 데이터 수집 및 캐싱 |
| 이중 시장 지원 | KOSPI/NASDAQ 비율 분할 투자 + 환율 환산 |
| 실거래 연동 | 한국투자증권 API를 통한 실제 매매 실행 (예정) |

### 주요 워크플로우

```
사용자: 파라미터 입력 (기간, 자금, 전략 설정)
  → Frontend: 폼 검증 → API 호출
    → Backend: 시장 데이터 수집/캐싱
      → Engine: 시그널 계산 → 일별 매매 시뮬레이션
    → Backend: 결과 응답
  → Frontend: 차트 · 지표 · 거래 내역 렌더링
```

매매 알고리즘 상세는 [algorithm.md](./05-algorithm.md)를 참고한다.
```

**Step 2: 커밋**

```bash
git add docs/01-architecture.md
git commit -m "docs: 아키텍처 문서 Core Features & Workflows 섹션 작성"
```

---

### Task 3: Technology Stack 섹션 작성

**Files:**
- Modify: `docs/01-architecture.md:16-17`
- Reference: `backend/pyproject.toml`, `frontend/package.json`, `docker-compose.yml`

**Step 1: 기술 스택 테이블 작성**

실제 의존성 파일에서 확인한 버전 정보를 기반으로 작성한다.

```markdown
## Technology Stack

### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.12+ | 런타임 |
| Django | 5.1 | 웹 프레임워크 |
| django-ninja | 1.3 | REST API (FastAPI 스타일) |
| FinanceDataReader | latest | 주가 · 시가총액 데이터 수집 |
| Pandas / NumPy | latest | 데이터 분석, 시뮬레이션 연산 |
| PyArrow | latest | 고속 데이터 캐싱 (Parquet) |
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
| TanStack Query | 5 | 서버 상태 관리 |
| Zustand | 5 | 클라이언트 상태 관리 |
| React Hook Form + Zod | latest | 폼 관리 · 유효성 검증 |

### Infrastructure

| 기술 | 용도 |
|------|------|
| Docker Compose | 로컬 개발 환경 오케스트레이션 |
| SQLite | 계정 관리, 거래 종목 관리 (예정) |
```

**Step 2: 커밋**

```bash
git add docs/01-architecture.md
git commit -m "docs: 아키텍처 문서 Technology Stack 섹션 작성"
```

---

### Task 4: Data Flow 섹션 작성

**Files:**
- Modify: `docs/01-architecture.md` (Core Features 뒤에 신규 섹션 삽입)
- Reference: `backend/apps/backtests/api.py`, `backend/core/engine/backtest.py`, `frontend/src/api/client.ts`, `frontend/src/hooks/useBacktest.ts`

**Step 1: 데이터 흐름 다이어그램 작성**

텍스트 기반 다이어그램으로 컴포넌트 간 통신 구조를 표현한다. 실제 코드의 호출 흐름을 확인하여 작성.

```markdown
## Data Flow

### 백테스트 실행 흐름

```
┌─────────────┐     POST /api/backtests/run     ┌──────────────┐
│  Frontend    │ ──────────────────────────────→  │  Backend API │
│  (React)     │                                  │  (Ninja)     │
│              │  ←────────────────────────────── │              │
│  Dashboard   │     JSON: 시뮬레이션 결과         │  Serializer  │
└─────────────┘                                   └──────┬───────┘
                                                         │
                                                         ▼
                                                  ┌──────────────┐
                                                  │  Engine      │
                                                  │  backtest.py │
                                                  └──────┬───────┘
                                                         │
                                              ┌──────────┼──────────┐
                                              ▼          ▼          ▼
                                        ┌──────────┐ ┌────────┐ ┌───────────┐
                                        │ signals  │ │ portfolio│ │ fetcher   │
                                        │ 시그널   │ │ 포트폴리오│ │ 데이터수집│
                                        └──────────┘ └────────┘ └─────┬─────┘
                                                                      │
                                                                      ▼
                                                               ┌─────────────┐
                                                               │ FinanceData │
                                                               │ Reader      │
                                                               │ + Cache     │
                                                               └─────────────┘
```

### 데이터 캐싱

Engine은 `FinanceDataReader` 호출 결과를 Parquet 형식으로 `.cache/` 디렉토리에 캐싱한다. 동일 기간 재조회 시 캐시를 우선 사용하여 API 호출을 최소화한다.
```

**Step 2: 커밋**

```bash
git add docs/01-architecture.md
git commit -m "docs: 아키텍처 문서 Data Flow 섹션 작성"
```

---

### Task 5: Project Structure 섹션 작성

**Files:**
- Modify: `docs/01-architecture.md:20-22`

**Step 1: 디렉토리 트리 작성**

실제 프로젝트 구조를 반영한 트리 + 역할 주석.

```markdown
## Project Structure

```
stock-simulator/
├── backend/                  # Django 백엔드
│   ├── apps/
│   │   ├── backtests/        # 백테스트 API · 스키마
│   │   └── market_data/      # 시장 데이터 API · 스키마
│   ├── config/               # Django 설정 (settings, urls)
│   ├── core/
│   │   ├── data/             # 데이터 수집 · 캐싱
│   │   └── engine/           # 백테스트 엔진 (시그널, 포트폴리오)
│   ├── tests/                # 백엔드 테스트
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                 # React 프론트엔드
│   ├── src/
│   │   ├── api/              # API 클라이언트 · 타입 정의
│   │   ├── components/       # UI 컴포넌트 (charts, forms, tables)
│   │   ├── features/         # 기능별 페이지 컴포넌트
│   │   ├── hooks/            # 커스텀 훅
│   │   └── utils/            # 유틸리티 (포맷터, 색상)
│   ├── Dockerfile
│   └── package.json
├── docs/                     # 프로젝트 문서
├── docker-compose.yml        # 로컬 개발 환경
└── CLAUDE.md                 # Claude Code 진입점
```
```

**Step 2: 커밋**

```bash
git add docs/01-architecture.md
git commit -m "docs: 아키텍처 문서 Project Structure 섹션 작성"
```

---

### Task 6: Modules 섹션 작성

**Files:**
- Modify: `docs/01-architecture.md:25-31`
- Reference: 각 모듈의 `__init__.py`, 주요 파일 확인

**Step 1: 모듈 한 줄 요약 작성**

각 모듈의 실제 코드를 확인하고 한 줄로 요약한다.

```markdown
## Modules

### Backend

| 모듈 | 역할 |
|------|------|
| `core/engine/backtest.py` | 백테스트 시뮬레이션 메인 루프 실행 |
| `core/engine/signals.py` | 연속 상승/하락, 긴급 손절 시그널 계산 |
| `core/engine/portfolio.py` | 포트폴리오 상태 관리 (보유 종목, 현금, 거래 기록) |
| `core/data/fetcher.py` | FinanceDataReader를 통한 시장 데이터 수집 |
| `core/data/cache.py` | Parquet 기반 데이터 캐싱 |
| `apps/backtests/` | 백테스트 실행 API 엔드포인트 · 요청/응답 스키마 |
| `apps/market_data/` | 시장 데이터 조회 API 엔드포인트 · 스키마 |

### Frontend

| 모듈 | 역할 |
|------|------|
| `api/` | Axios 기반 API 클라이언트 · TypeScript 타입 정의 |
| `features/backtest/` | 백테스트 대시보드 · 결과 페이지 |
| `components/charts/` | 자산 변동 차트, 벤치마크 비교 차트 |
| `components/forms/` | 백테스트 파라미터 입력 폼 |
| `components/tables/` | 거래 내역 테이블 |
| `components/metrics/` | 주요 지표 카드 (수익률, MDD 등) |
| `hooks/` | 백테스트 실행 · 데이터 페칭 커스텀 훅 |
| `utils/` | 숫자 포맷터, 색상 유틸리티 |
```

**Step 2: 커밋**

```bash
git add docs/01-architecture.md
git commit -m "docs: 아키텍처 문서 Modules 섹션 작성"
```

---

### Task 7: Infrastructure & Deployment 섹션 작성

**Files:**
- Modify: `docs/01-architecture.md` (마지막에 신규 섹션 추가)
- Reference: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/.env.example`

**Step 1: 인프라 구성 작성**

Docker Compose 구성과 서비스 간 연결, 환경 변수, 포트 매핑을 설명한다.

```markdown
## Infrastructure & Deployment

### Docker Compose 구성

| 서비스 | 이미지 | 포트 | 역할 |
|--------|--------|------|------|
| `backend` | `backend/Dockerfile` | 8000 | Django API 서버 |
| `frontend` | `frontend/Dockerfile` | 5173 | Vite 개발 서버 |

- `frontend`는 `backend`에 의존한다 (`depends_on`)
- 백엔드 캐시 데이터는 `backend_cache` 볼륨으로 영속화

### 환경 변수

백엔드 환경 변수는 `backend/.env`로 관리한다. 템플릿: `backend/.env.example`

### 포트 매핑

| 서비스 | 호스트 | 컨테이너 |
|--------|--------|----------|
| Backend API | `localhost:8000` | `0.0.0.0:8000` |
| Frontend Dev | `localhost:5173` | `0.0.0.0:5173` |
```

**Step 2: 커밋**

```bash
git add docs/01-architecture.md
git commit -m "docs: 아키텍처 문서 Infrastructure & Deployment 섹션 작성"
```

---

### Task 8: 최종 검토 및 CLAUDE.md 정합성 확인

**Step 1: 문서 전체 통독**

`docs/01-architecture.md` 전체를 읽고 다음을 확인:
- 섹션 간 흐름이 자연스러운가
- 다른 문서(`05-algorithm.md`, `02-development.md`)와 내용 중복이 없는가
- 설계안(`docs/plans/2026-02-25-architecture-doc-design.md`)의 모든 항목이 반영되었는가

**Step 2: CLAUDE.md 설명 정합성 확인**

CLAUDE.md에서 `01-architecture.md`의 설명이 실제 내용과 맞는지 확인. 필요 시 갱신.

**Step 3: 커밋 (수정 사항이 있는 경우)**

```bash
git add docs/01-architecture.md CLAUDE.md
git commit -m "docs: 아키텍처 문서 최종 검토 및 정합성 확인"
```
