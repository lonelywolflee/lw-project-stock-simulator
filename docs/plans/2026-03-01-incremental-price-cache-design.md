# 가격 데이터 증분 캐시 설계

## 문제

현재 `_load_price_from_db`는 `last_date < end`로 완전성을 판단한다.
비거래일(주말, 공휴일)로 인해 end 날짜에 데이터가 없으면
매번 네트워크를 재요청하여 캐시가 동작하지 않는다.

## 목표

1. 한 번 fetch한 기간은 재요청하지 않는다
2. 부분 캐시 시 미캐시 범위만 네트워크에서 fetch한다
3. 거래일/비거래일을 구분하여 "데이터 없음"이 정상인지 판단한다

## 전제

- FDR 범위 fetch 시 반환된 데이터는 완전하다 (부분 실패 없음)
- 반환되지 않은 날짜 = 비거래일
- 네트워크 오류 시 아무것도 저장하지 않는다 (all-or-nothing)

## 모델

### PriceFetchCoverage (신규)

일자별 fetch 커버리지를 추적한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| code | CharField(20) | 종목코드 or "KS11" |
| date | DateField | 날짜 |
| has_data | BooleanField | True=거래일(데이터 존재), False=비거래일(데이터 없음이 정상) |

- unique_together: (code, date)
- db_table: `market_data_price_fetch_coverage`

## 데이터 흐름

### 현재

```
fetch_price_data(code, start, end)
  → _load_price_from_db  # last_date < end이면 None → 전체 재fetch
  → 네트워크 전체 범위 fetch
  → _save_price_to_db
```

### 변경 후

```
fetch_price_data(code, start, end)
  → _find_uncovered_ranges(code, start, end)
  │   └─ PriceFetchCoverage에서 미커버 날짜 조회
  │   └─ 연속 날짜를 구간으로 묶음
  ├─ 미커버 구간 없음 → DB에서 바로 로드
  └─ 미커버 구간 있음 → 각 구간별 네트워크 fetch
       ├─ 성공 → _save_price_to_db + _save_coverage
       └─ 실패 → 예외 (저장 없음)
  → _load_price_from_db(code, start, end)  # 전체 결과 반환
```

### 예시

```
요청: fetch_price_data("005930", "2024-01-02", "2024-01-10")

Case 1: 완전 미캐시
  uncovered: [(01-02, 01-10)]
  FDR 반환: 01-02, 01-03, 01-04, 01-08, 01-09, 01-10 (01-05~07 주말/공휴일)
  StockDailyPrice: 6개 레코드 저장
  PriceFetchCoverage: 9개 레코드 (6개 has_data=True, 3개 has_data=False)

Case 2: 01-02~01-04 캐시됨
  uncovered: [(01-05, 01-10)]
  FDR fetch: 01-05~01-10만 요청
  나머지 저장 + 커버리지 기록
  DB에서 01-02~01-10 전체 로드

Case 3: 완전 캐시
  uncovered: []
  네트워크 요청 없음, DB에서 바로 반환

Case 4: 다중 미캐시 구간 (01-02~04 캐시, 01-05 미캐시, 01-06~07 캐시, 01-08~10 미캐시)
  uncovered: [(01-05, 01-05), (01-08, 01-10)]
  각 구간별로 별도 네트워크 fetch
```

## 변경 파일

| 레이어 | 파일 | 변경 |
|--------|------|------|
| apps | `market_data/models.py` | `PriceFetchCoverage` 모델 추가 |
| apps | `market_data/services.py` | `_find_uncovered_ranges`, `_save_coverage` 추가, `_load_price_from_db` 수정 (last_date 체크 제거), `fetch_price_data`·`fetch_kospi_index` 증분 로직 적용 |
| core | `data/fetcher.py` | `fetch_price_data_raw` 추가 (네트워크 전용, 빈 결과 허용) |
| tests | `tests/` | 증분 캐시 시나리오 테스트 추가 |

## 설계 결정

- **별도 커버리지 테이블**: 가격 데이터와 커버리지 관심사를 분리한다
- **일자별 추적**: 범위 기반보다 구현이 단순하고 부분 겹침 처리가 쉽다
- **core 최소 변경**: 증분 오케스트레이션은 services 레이어에서 담당하여 의존성 역전 원칙을 유지한다
- **all-or-nothing**: 네트워크 실패 시 해당 구간의 가격·커버리지 모두 저장하지 않는다
