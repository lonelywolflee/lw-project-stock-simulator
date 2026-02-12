# frontend/src/ 레이어 개발 가이드

## 역할

React SPA — 백테스트 파라미터 입력 폼, Recharts 차트 시각화, 지표 카드 및 거래내역 테이블 표시.

## 실행

```bash
cd frontend && npm run dev
```

## 기술 스택

- **React 19** + **TypeScript** + **Vite** — SPA 프레임워크
- **shadcn/ui** + **Tailwind CSS v4** — 컴포넌트 라이브러리
- **TanStack Query v5** — 서버 상태 관리 (백테스트 mutation)
- **Recharts** — 차트 시각화
- **React Hook Form** + **Zod** — 폼 유효성 검증

## 모듈 구성

### `api/` — API 클라이언트

- `types.ts`: 백엔드 Pydantic 스키마와 1:1 매핑되는 TypeScript 인터페이스
- `client.ts`: Axios 인스턴스 (baseURL="/api", timeout=600s) + `runBacktest()` 단일 함수

### `hooks/` — TanStack Query 커스텀 훅

- `useBacktest.ts`: `useRunBacktest()` — `useMutation`으로 동기 백테스트 실행

### `components/` — 재사용 UI 컴포넌트

- `forms/BacktestForm.tsx`: React Hook Form + Zod 유효성 검증, 4개 카드 섹션 (기본 설정, 시장 비율, 전략 설정, 자금 설정)
- `charts/AssetChart.tsx`: Recharts AreaChart — 현금/주식평가액 스택 + 총자산 Line 오버레이
- `charts/ComparisonChart.tsx`: Recharts LineChart — 포트폴리오 vs KOSPI/NASDAQ 수익률 비교 (Base=100)
- `metrics/MetricsCards.tsx`: 5개 지표 카드 (수익률, MDD, 거래수, 승률, 수수료)
- `tables/TradeTable.tsx`: shadcn Table — 9열 거래내역 (시장별 KRW/USD 통화 포맷)

### `features/` — 페이지 단위 컴포넌트

- `backtest/BacktestDashboard.tsx`: 메인 페이지 — aside(폼) + main(로딩/결과/빈 상태) 그리드 레이아웃
- `backtest/BacktestResults.tsx`: 결과 컨테이너 — MetricsCards + Tabs (자산 추이, 벤치마크 비교, 거래 내역)

### `utils/` — 유틸리티

- `formatters.ts`: 한국 금융 포매터 (formatKRW, formatUSD, formatPercent, formatDate 등)
- `colors.ts`: 금융 색상 상수 (상승=빨강, 하락=파랑) + getProfitColor 유틸리티

## 디자인 규칙

- **한국 금융 컨벤션**: 상승=빨강(red), 하락=파랑(blue)
- **통화 포맷**: KOSPI 거래는 KRW, NASDAQ 거래는 USD로 표시
- **상태 관리**: TanStack Query의 `useMutation` 하나로 관리 (별도 클라이언트 상태 없음)
