# KOSPI-DESC Fallback 설계

## 문제

`fdr.StockListing("KOSPI")`가 KRX API 장애로 실패할 수 있다.
단일 소스 의존은 백테스트 실행 자체를 불가능하게 만든다.

## 목표

1. KOSPI 실패 시 KOSPI-DESC로 fallback하여 종목 목록을 확보한다
2. KOSPI-DESC에는 시가총액이 없으므로, 거래대금(volume × close)으로 대체한다
3. 사용자에게 데이터 품질 저하를 SSE log 이벤트로 안내한다

## 설계

### Fallback 흐름

```
fetch_stock_listing("KOSPI") 호출
  → fdr.StockListing("KOSPI") 시도 (retry=1)
  → 실패 시 fdr.StockListing("KOSPI-DESC") 시도 (retry=1)
    → Code, Name만 반환 (Marcap 없음)
  → 둘 다 실패 → DB fallback → 없으면 예외
```

- listing은 retry=1 (기본값 3 대신)
- KOSPI-DESC 응답에서 Code, Name만 추출하고 나머지 컬럼(Sector, Industry 등)은 버린다

### market_cap 대체 계산

`_rank_buy_candidates`에서 `sort_method="market_cap"` 시:
- `cap_map`에서 종목의 Marcap이 0 또는 None이면
- 해당 종목의 최신 거래일 `volume × close`로 대체

### 안내 문구

기존 SSE `log` 이벤트로 전달 (프론트엔드 수정 불필요):
- KOSPI-DESC 사용 시: "KOSPI 목록 조회 실패로 KOSPI-DESC를 사용합니다. 실시간 시가총액이 반영되지 않습니다."
- 시총 대체 계산 시: "시가총액 정보가 없는 종목은 거래대금(거래량×종가) 기준으로 산정합니다."

### 변경 파일

| 파일 | 변경 |
|------|------|
| `core/data/fetcher.py` | KOSPI → KOSPI-DESC fallback, listing retry=1 |
| `core/engine/backtest.py` | `_rank_buy_candidates` Marcap 0 → volume×close 대체 |
| `apps/backtests/api.py` | Marcap 유무 확인 + log 이벤트 전송 |

### 설계 결정

- fallback 판단은 DataFrame에 Marcap 컬럼 유무로 한다 — 명시적 플래그 불필요
- `_save_listing_to_db`는 이미 Marcap 없으면 market_cap 업데이트 안 하도록 구현됨
- 안내 문구는 기존 `log` SSE 이벤트를 재활용한다
