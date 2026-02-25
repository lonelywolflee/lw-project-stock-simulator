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



## Technology Stack



## Project Structure




## Modules

### Backend Modules


### Frontend Modules

