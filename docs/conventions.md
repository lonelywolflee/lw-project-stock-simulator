# 코딩 규칙 및 주의사항

## 아키텍처 규칙

- **Engine 순수 로직**: `backend/core/engine/`은 외부 I/O 없는 순수 로직. Django 의존 금지
- **일별 루프 순서**: SELL → BUY → SNAPSHOT (매도 우선으로 현금 확보 후 매수)
- **동기 API**: 백테스트는 동기 실행 (POST → 결과 즉시 반환). axios timeout 600초

## 이중 시장 규칙

- NASDAQ 포트폴리오는 USD 기준 운영
- 합산 시 일별 USD/KRW 환율로 KRW 환산
- KOSPI:NASDAQ 비율은 `kospi_ratio` (0~100)로 조절

## Import 규칙

- Backend: `core.engine.*`, `core.data.*` (NOT `src.engine.*`)
- `backend/core/`는 Django app이 아님 — `INSTALLED_APPS`에 등록하지 않는다

## UI 컨벤션

- **한국 금융 컬러**: 상승=빨강(red), 하락=파랑(blue) — 미국 컨벤션과 반대
- **통화 포맷**: KOSPI 거래는 KRW, NASDAQ 거래는 USD로 표시

## 주의사항 (Gotchas)

- NASDAQ 종목 목록의 코드 컬럼은 `"Symbol"` (KOSPI는 `"Code"`) — 매핑 시 주의
- 대규모 백테스트(이중 시장, 장기간) 시 HTTP 요청이 수 분 소요될 수 있음 — Production 배포 시 gunicorn `--timeout 600` 필요
- `apps/*/models.py`와 `apps/*/admin.py`는 빈 파일 — DB 모델/Admin 미사용. 마이그레이션, `makemigrations` 불필요
- `frontend/src/stores/` 디렉토리 없음 — Zustand 제거됨. 클라이언트 상태는 TanStack Query `useMutation` 하나로 관리 (별도 클라이언트 상태 없음)
- `core/data/fetcher.py`의 모든 네트워크 요청은 `_retry()` 지수 백오프(최대 3회)를 거친다 — 직접 FinanceDataReader 호출 금지

## 커밋 규칙

- 커밋 타입: `docs:`, `feat:`, `refactor:`, `fix:` (한국어 메시지)
- `/commit` 커맨드 사용 시 자동으로 목적별 분리 커밋
