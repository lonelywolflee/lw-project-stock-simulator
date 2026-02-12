# backend/core/data/ 레이어 개발 가이드

## 역할

외부 데이터 수집 (FinanceDataReader) + Parquet 캐시.

## 모듈 구성

### `fetcher.py` — FinanceDataReader 래퍼

- `_retry(func, *args, retries, **kwargs)`: 지수 백오프 재시도 (최대 3회, `RETRY_BASE_DELAY * 2^attempt`)
- `fetch_stock_listing(market)`: 상장 종목 목록 반환 (`"KOSPI"` 또는 `"NASDAQ"`)
- `fetch_price_data(code, start, end)`: 개별 종목 일별 OHLCV. 캐시 우선 확인
- `fetch_all_prices(codes, start, end, progress_callback)`: 여러 종목을 순차 수집하여 `dict[str, pd.DataFrame]` 반환
- `fetch_kospi_index(start, end)`: KOSPI 지수 (KS11)
- `fetch_nasdaq_index(start, end)`: NASDAQ Composite 지수 (IXIC)
- `fetch_exchange_rate(start, end)`: USD/KRW 일별 환율

### `cache.py` — Parquet 파일 기반 로컬 캐시

- 캐시 디렉토리: `.cache/`
- `get_cache_path(code, start, end)` → `{code}_{start}_{end}.parquet` 경로 반환
- `load_from_cache(code, start, end)` → 파일 존재 시 DataFrame 반환, 없으면 `None`
- `save_to_cache(code, start, end, df)` → DataFrame을 Parquet으로 저장

## 가격 데이터 형식

`dict[str, pd.DataFrame]` — 종목코드 → OHLCV DataFrame (DatetimeIndex).

## 주의사항

- 모든 네트워크 요청은 `_retry()`를 거친다
- 캐시 키는 종목코드 + 기간 조합이므로, 동일 종목이라도 기간이 다르면 별도 캐시
- NASDAQ 종목 목록의 코드 컬럼은 `"Symbol"` (KOSPI는 `"Code"`)
