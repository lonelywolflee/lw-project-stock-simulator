# Architecture Document Redesign

## Context

`docs/01-architecture.md` 문서를 재작성한다. Overview만 완성된 상태에서 나머지 섹션의 구조와 내용 수준을 결정한다.

## Decisions

- **독자**: AI 에이전트 + 인간 개발자 (Single Source of Truth)
- **Design Principles**: 사용자가 정의한 7개 원칙을 간결하게 정리
- **Core Features & Workflows**: 고수준 기능 목록 + 사용자 흐름도 (알고리즘 상세는 `05-algorithm.md`에 위임)
- **Modules**: 모듈별 한 줄 요약 (API 시그니처는 코드가 진실의 소스)
- **Data Flow**: 신규 추가 — 컴포넌트 간 통신 구조
- **Infrastructure & Deployment**: 신규 추가 — Docker Compose 구성, 환경 변수, 포트 매핑

## Section Structure

```
# Architecture

## Overview                          ← 유지 (완성됨)

## Design Principles                 ← 7개 원칙 정리
  1. 모듈화/재사용 — 중복 제거
  2. Functional Programming — 가독성, 테스트 용이성 최우선
  3. 비동기 + 친절한 UX — 진행 상태 표시
  4. Zero Trust 보안 — 인증/인가 필수, 데이터 위변조 검수
  5. 레이어 분리 — 목적 명확, 경계 분명, 언어/서비스별 best practice
  6. 최신 안정 스택 — 2026년 기준
  7. 보수적 예외 처리 — 중복 없이 레이어별 책임 분리

## Core Features & Workflows         ← 고수준 기능 + 흐름도
  - 핵심 기능 리스트
  - 주요 워크플로우 (파라미터 입력 → 실행 → 결과 확인)

## Technology Stack                  ← 테이블 형태
  - Backend: Python, Django, django-ninja, pandas 등
  - Frontend: React 19, Vite 7, TailwindCSS 4, Recharts 등
  - Infra: Docker Compose, SQLite

## Data Flow                         ← 신규
  - Frontend → Backend API → Engine → DataFetcher 간 흐름

## Project Structure                 ← 디렉토리 트리 + 역할 주석

## Modules                           ← 모듈별 한 줄 요약
  - Backend: core/engine, core/data, apps/backtests, apps/market_data
  - Frontend: api, components, features, hooks, utils

## Infrastructure & Deployment       ← 신규
  - Docker Compose 서비스 구성
  - 환경 변수, 포트 매핑
```

## Excluded

- API 시그니처 상세 → 코드가 진실의 소스
- 알고리즘 명세 → `05-algorithm.md`에 이미 존재
- ERD/DB 스키마 → SQLite 도입 시 별도 문서로 분리 예정

## Boundary with Other Docs

- `02-development.md`: "어떻게 실행하는가" (환경 설정, 명령어)
- `01-architecture.md`: "왜 이 구조인가" (설계 근거, 전체 그림)
- `05-algorithm.md`: 매매 알고리즘 상세 명세
