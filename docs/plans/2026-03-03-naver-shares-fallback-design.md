# 네이버 증권 상장주식수 Fallback 설계

## Context

백테스트 매수 후보 랭킹 시 시가총액(`listing_shares × 종가`) 기준으로 정렬한다.
FDR `StockListing("KOSPI")` 호출이 실패하여 DESC variant로 fallback하면
`listing_shares`가 없어 `거래량 × 종가`라는 부정확한 대안을 사용하게 된다.

네이버 증권에서 개별 종목의 상장주식수를 스크래핑하는 중간 fallback을 추가하여
정확도를 높인다. 매수 시그널이 발생한 후보 종목만 on-demand로 조회하므로
호출량이 적고, DB 캐시(날짜 기준)로 중복 호출을 방지한다.

## Fallback 체인 (3단계)

```
shares_map[code] > 0?
  → YES → shares × 종가 (끝)
  → NO  → resolve_shares(code) 콜백 호출
            → DB에 오늘 기록 있음?
                → YES → DB의 listing_shares 반환
                → NO  → 네이버 증권 스크래핑
                    → 성공? → DB 업데이트 + listing_shares 반환
                    → 실패? → None 반환
          → shares 반환됨?
              → YES → shares × 종가 (끝)
              → NO  → 거래량 × 종가 fallback (끝)
```

## 변경 파일

### 1. `apps/market_data/models.py` — StockListing 모델

`listing_shares_updated_at = DateField(null=True, blank=True)` 필드 추가.
FDR 일괄 저장 시에도 `today()` 기록, 네이버 개별 조회 시에도 동일.

### 2. `core/data/fetcher.py` — 네이버 스크래핑 함수

```
fetch_listing_shares_from_naver(code: str) -> int | None
```

- `GET https://finance.naver.com/item/main.naver?code={code}`
- `<div id="tab_con1">` 내부 `<th>상장주식수</th>` 옆 `<em>` 태그 파싱
- 기존 `_retry()` 재사용 (retries=1)
- 실패 시 `None` 반환

### 3. `apps/market_data/services.py` — resolve 콜백

```
_resolve_listing_shares(market: str, code: str) -> int | None
```

- DB 조회: `listing_shares > 0` and `listing_shares_updated_at == today()` → 캐시 히트
- 캐시 미스 → `fetch_listing_shares_from_naver(code)` 호출
- 성공 시 DB 업데이트 (`listing_shares`, `listing_shares_updated_at`)
- 반환: `int | None`

### 4. `core/engine/backtest.py` — _rank_buy_candidates

시그니처에 `resolve_shares: Callable[[str], int | None] | None = None` 추가.

`_effective_cap` 내부:
1. `shares_map.get(code)` 확인
2. 없으면 `resolve_shares(code)` 호출 (콜백이 있을 때만)
3. 그래도 없으면 `volume × close` fallback

### 5. `apps/backtests/api.py` — 콜백 주입

`run_backtest()` 호출 시 `resolve_shares=lambda code: _resolve_listing_shares("KOSPI", code)` 전달.

### 6. `apps/market_data/services.py` — _save_listing_to_db 수정

FDR에서 일괄 저장 시 `listing_shares`가 있으면 `listing_shares_updated_at=today()`도 함께 저장.

## 테스트 계획

- `test_fetcher.py`: `fetch_listing_shares_from_naver` 단위 테스트 (mock HTML 응답)
- `test_backtest.py`: `resolve_shares` 콜백 동작 테스트 (mock 콜백)
- `test_fetcher_db.py`: DB 캐시 히트/미스 시나리오, `listing_shares_updated_at` 갱신 확인

## 검증 방법

1. `python -m pytest tests/ -v` 전체 테스트 통과
2. 실제 네이버 증권 URL 호출 확인 (수동): `fetch_listing_shares_from_naver("005930")` → 삼성전자 상장주식수 반환
