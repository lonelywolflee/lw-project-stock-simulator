# 테스트

## 개요

Backend 테스트는 Django에 의존하지 않는 순수 Python 테스트로, `pytest`만으로 실행한다. pytest-django 플러그인은 불필요하다.

## 실행 방법

```bash
# 전체 테스트
cd backend && uv run pytest tests/ -v

# 단일 파일
cd backend && uv run pytest tests/test_backtest.py -v

# 특정 클래스 또는 메서드
cd backend && uv run pytest tests/test_backtest.py::TestBacktest::test_basic_backtest -v
```

## 테스트 구조

- 테스트 위치: `backend/tests/`
- Import 규칙: `core.engine.*` (Django app 경로 아님)

## 테스트 데이터 헬퍼

테스트에서는 외부 API를 호출하지 않고 합성 데이터를 사용한다:

- `_make_price_df()` — 가격 DataFrame 생성 (DatetimeIndex, OHLCV 컬럼)
- `_make_listing()` — 상장 종목 목록 DataFrame 생성

## Frontend 테스트

미구성 상태. 추후 Vitest 도입 예정.
