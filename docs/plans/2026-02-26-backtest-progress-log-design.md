# 백테스트 실시간 진행 로그 — 디자인 문서

## 개요

백테스트 실행 중 터미널 스타일 진행 로그를 실시간으로 보여주는 기능.
사용자가 하염없이 기다리는 대신 현재 진행 상황을 시각적으로 확인할 수 있다.

## 아키텍처

```
[Frontend]                         [Backend]
BacktestDashboard                  POST /api/backtests/run (SSE)
  └─ BacktestProgressLog           └─ StreamingHttpResponse
       ├─ EventSource 연결              ├─ Phase 1: 종목 로딩 → event
       ├─ 로그 라인 렌더링               ├─ Phase 2: 주가 수집 → event (batch)
       ├─ 프로그레스바 렌더링             ├─ Phase 3: 시뮬레이션 → event (매매 포함)
       └─ 완료 시 결과 JSON 수신         └─ Phase 4: 완료 → result event
```

- 기존 `/api/backtests/run` 동기 엔드포인트를 SSE 스트리밍으로 교체
- Django `StreamingHttpResponse` + `text/event-stream`
- 프론트엔드 `EventSource` API로 소비

## 백엔드 SSE 이벤트 설계

### 이벤트 타입

| 이벤트 | 용도 | payload |
|--------|------|---------|
| `phase` | 단계 시작 알림 | `{phase, total, message}` |
| `progress` | 진행률 (프로그레스바) | `{phase, current, total, message}` |
| `trade` | 매매 발생 | `{phase, date, side, name, code, price, quantity, profit_pct}` |
| `error` | 에러 발생 | `{message}` |
| `result` | 최종 결과 JSON | 기존 BacktestResult 전체 |

### 이벤트 예시

```
event: phase
data: {"phase": 1, "total": 4, "message": "종목 목록 로딩 중..."}

event: progress
data: {"phase": 2, "current": 142, "total": 926, "message": "주가 데이터 수집 중..."}

event: trade
data: {"phase": 3, "date": "2024-03-15", "side": "BUY", "name": "삼성전자", "code": "005930", "price": 72400, "quantity": 138}

event: trade
data: {"phase": 3, "date": "2024-03-18", "side": "SELL", "name": "SK하이닉스", "code": "000660", "profit_pct": 4.2}

event: result
data: { ...전체 BacktestResult JSON... }
```

## 프론트엔드 컴포넌트 설계

### BacktestProgressLog

- 고정 높이(300px) 터미널 스타일 박스, 자동 하단 스크롤
- 기존 다크 테마(`glass-card`, `font-mono-data`) 활용
- 로그 라인 타입별 렌더링:
  - `phase` → `[1/4] 종목 목록 로딩 중...` (mint 색상)
  - `progress` → 텍스트 프로그레스바 `████████░░░░ 142/926 (15.3%)`
  - `trade BUY` → `↗ 매수: 삼성전자 — 72,400원 × 138주` (profit 색상)
  - `trade SELL` → `↘ 매도: SK하이닉스 — +4.2%` (profit/loss 색상)
  - 완료 → `✓ 완료 — 총 47건, 수익률 +8.3% (12.3초)`

### BacktestDashboard 흐름

1. 실행 버튼 클릭 → `EventSource` 연결 → 로그 영역 표시
2. SSE 이벤트 수신 → 로그 라인 추가
3. `result` 이벤트 수신 → 결과 저장, 로그 접기(토글 가능), 결과 차트/테이블 표시

### useBacktestStream 훅

- React Query mutation 대신 `EventSource` 기반 커스텀 훅
- 상태: `logs`, `progress`, `result`, `status` (idle/streaming/done/error)
- 기존 `useRunBacktest` 훅 교체

## 에러 처리

- 네트워크 끊김: `onerror` → 로그에 에러 표시 + 재시도 버튼
- 백엔드 예외: `event: error` → 로그에 에러 메시지
- 타임아웃: 60초 이상 이벤트 없으면 연결 종료
- SSE 자동 재연결 방지: `result`/`error` 수신 시 `.close()` 호출

## 결정 사항

- 실시간 통신: SSE (StreamingHttpResponse)
- 메시지 세부 수준: 상세 이벤트 로그 (매매 이벤트 포함)
- 프로그레스바: 텍스트 기반 (████░░░░), 터미널 테마와 조화
- 완료 후 전환: 로그 접기 + 결과 표시 (토글 가능)
- 로그 영역: 고정 높이 300px + 자동 하단 스크롤
