# KOSPI 알고리즘 거래 시뮬레이터

FinanceDataReader로 KOSPI 과거 데이터를 수집하고, 시그널 기반 백테스트 엔진으로 매매 전략을 시뮬레이션한 뒤, React 대시보드로 결과를 시각화하는 풀스택 증권 거래 시뮬레이터.

## 주요 기능

- **시그널 기반 매매**: n일 연속 상승 매수, m일 연속 하락 매도, 긴급 손절
- **대시보드**: 자산 추이 차트, 벤치마크 비교, 핵심 지표 카드, 거래 내역 테이블
- **인프라리스**: 외부 DB/큐 없이 동기 API로 즉시 결과 반환

## 기술 스택

Django 5.x + django-ninja | React 19 + TypeScript + Vite | shadcn/ui + Tailwind CSS v4 | TanStack Query v5 | Recharts

## 프로젝트 구조

```
backend/   → Django REST API + 백테스트 엔진 + 데이터 수집
frontend/  → React SPA 대시보드
docs/      → 프로젝트 문서
```

## 시작하기

환경 설정, 실행 방법, 명령어 레퍼런스는 [개발 가이드](docs/development.md)를 참고한다.

## 문서

| 문서 | 내용 |
|------|------|
| [아키텍처](docs/01-architecture.md) | 시스템 구조, 기술 스택, 주요 파일 |
| [개발 가이드](docs/02-development.md) | 환경 설정, 실행, 명령어 |
| [코딩 규칙](docs/03-conventions.md) | 규칙, 주의사항 |
| [테스트](docs/04-testing.md) | 테스트 전략, 실행 방법 |
| [매매 알고리즘](docs/05-algorithm.md) | 알고리즘 상세 명세 |
| [Backend](backend/README.md) | 백엔드 빌드/실행 |
| [Frontend](frontend/README.md) | 프론트엔드 빌드/실행 |
