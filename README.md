# KOSPI + NASDAQ 이중 시장 알고리즘 거래 시뮬레이터

FinanceDataReader로 KOSPI/NASDAQ 과거 데이터를 수집하고, 시그널 기반 백테스트 엔진으로 매매 전략을 시뮬레이션한 뒤, React 대시보드로 결과를 시각화하는 풀스택 증권 거래 시뮬레이터.

## 기술 스택

### Backend
- **Django** + **django-ninja** — REST API (동기 실행, 외부 인프라 불필요)
- **FinanceDataReader** — 주가, 지수, 환율 데이터 수집
- **Pandas / NumPy** — 데이터 분석 및 시뮬레이션 로직

### Frontend
- **React 19** + **TypeScript** + **Vite** — SPA
- **shadcn/ui** + **Tailwind CSS v4** — 컴포넌트 라이브러리
- **TanStack Query v5** — 서버 상태 관리
- **Recharts** — 차트 시각화

## 주요 기능

### 매매 알고리즘
- **매수**: n일 연속 상승 종목을 시가총액 또는 수익률 순으로 정렬하여 종목당 최대 금액까지 매수
- **매도**: m일 연속 하락 시 전량 매도, 당일 y% 이상 급락 시 긴급 손절
- **수수료**: 매수/매도 시 k% 차감

### 이중 시장 지원
- KOSPI/NASDAQ 비율 조절 가능 (0~100%)
- NASDAQ 포트폴리오는 USD 기준 운영, 합산 시 일별 환율로 KRW 환산

### 시각화
- 자산 추이 영역 차트 (현금 + 주식 평가액)
- 포트폴리오 vs KOSPI/NASDAQ 벤치마크 수익률 비교 (Base=100)
- 핵심 지표 카드 (수익률, MDD, 거래수, 승률, 수수료)
- 거래 내역 테이블

## 실행 방법

```bash
# Backend
cp backend/.env.example backend/.env  # 필요 시 값 수정
cd backend && uv sync
uv run python manage.py runserver

# Frontend (별도 터미널)
cd frontend && npm install
npm run dev

# Docker (전체 스택)
docker compose up
```

## 테스트

```bash
cd backend && uv run pytest tests/ -v
```

## 프로젝트 구조

```
backend/
├── config/         # Django 설정 (settings, urls)
├── apps/
│   ├── backtests/  # 백테스트 API, 스키마, 직렬화
│   └── market_data/ # 종목 데이터 API
├── core/
│   ├── engine/     # 시그널 감지, 포트폴리오, 백테스트 엔진 (순수 로직)
│   └── data/       # FinanceDataReader 래퍼 + Parquet 캐시
└── tests/          # pytest 기반 단위/통합 테스트

frontend/
├── src/
│   ├── api/        # Axios 클라이언트 + TypeScript 타입
│   ├── hooks/      # TanStack Query 커스텀 훅
│   ├── components/ # 재사용 UI 컴포넌트 (폼, 차트, 테이블, 메트릭)
│   ├── features/   # 페이지 단위 컴포넌트 (BacktestDashboard)
│   └── utils/      # 포매터, 색상 유틸리티
└── ...
```
