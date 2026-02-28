# 의존성 역전 리팩토링 설계

## 목표

`core/` 모듈이 `apps/`에 의존하는 위반을 제거하여 레이어 규칙을 준수한다.

## 규칙

1. 멱등성을 가진 함수형 프로그래밍 (외부 호출 제외)
2. `config/`: 다른 모듈 의존 없음
3. `core/`: `config` 외 다른 모듈 의존 금지
4. `apps/`: `config` 및 `core` 기능 사용
5. 1급 시민 함수로 의존성 관계 준수

## 현재 위반

`core/data/fetcher.py`가 `apps.market_data.models`를 5곳에서 import.

## 해결: 콜백 주입

- `core/data/fetcher.py`: DB import 제거, DB 접근 함수를 콜백 파라미터로 수신
- `apps/market_data/services.py`: DB 접근 로직 + core fetcher 조합
- `apps/backtests/api.py`, `apps/market_data/api.py`: services에서 import

## 변경 파일

| 파일 | 변경 |
|------|------|
| `core/data/fetcher.py` | apps import 제거, 콜백 파라미터 추가 |
| `apps/market_data/services.py` | 신규: DB 접근 + core fetcher 조합 |
| `apps/market_data/api.py` | services에서 import |
| `apps/backtests/api.py` | services에서 import |
| `tests/test_fetcher_db.py` | services 테스트로 변경 |
