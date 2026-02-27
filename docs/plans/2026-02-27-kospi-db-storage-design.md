# KOSPI 종목/가격 데이터 DB 저장 설계

## 목표

KOSPI 종목 정보와 종목/지수 일별 가격 데이터를 DB에 저장하여
파일 캐시를 대체하고, 안정적인 데이터 조회 체계를 구축한다.

## 요구사항

1. 종목 정보를 하루 1회 배치로 fetch. 배치 미실행 시 요청 시점에 fetch. 실패 시 기존 DB 데이터 사용
2. 종목별 일별 가격: DB에 있으면 DB 사용, 없으면 fetch 후 DB 저장
3. 파일 캐시(Parquet) 제거 — DB로 대체
4. 가격 fetch 실패 시 시뮬레이션 진행 불가

## 모델

### BatchMeta

배치 작업의 마지막 실행 일자를 추적한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| job_name | CharField(unique) | 작업 이름 (e.g. "kospi_listing") |
| last_fetched_date | DateField | 마지막 fetch 성공 일자 |
| updated_at | DateTimeField(auto) | 레코드 수정 시각 |

### StockListing

KOSPI 상장 종목 정보.

| 필드 | 타입 | 설명 |
|------|------|------|
| code | CharField(unique, db_index) | 종목코드 (e.g. "005930") |
| name | CharField | 종목명 (e.g. "삼성전자") |
| market_cap | BigIntegerField(nullable) | 시가총액 |

### StockDailyPrice

종목 및 지수의 일별 OHLCV 데이터.

| 필드 | 타입 | 설명 |
|------|------|------|
| code | CharField(db_index) | 종목코드 or "KS11" |
| date | DateField(db_index) | 거래일 |
| open | FloatField | 시가 |
| high | FloatField | 고가 |
| low | FloatField | 저가 |
| close | FloatField | 종가 |
| volume | BigIntegerField | 거래량 |
| is_index | BooleanField(default=False) | True면 지수 |

- unique_together: (code, date)

## 데이터 흐름

### 종목 목록

```
요청 → BatchMeta("kospi_listing") 확인
  ├─ 오늘 이미 fetch → DB StockListing 조회
  └─ fetch 안 함 → FinanceDataReader 호출
       ├─ 성공 → DB upsert + BatchMeta 갱신
       └─ 실패 → DB에 기존 데이터 있으면 사용, 없으면 에러
```

### 종목별 일별 가격

```
요청(code, start, end) → StockDailyPrice에서 해당 범위 조회
  ├─ 모든 거래일 존재 → DataFrame 반환
  └─ 누락 → FinanceDataReader로 전체 범위 fetch
       ├─ 성공 → DB bulk insert → 반환
       └─ 실패 → 에러 (시뮬레이션 불가)
```

## 변경 파일

| 파일 | 변경 |
|------|------|
| `apps/market_data/models.py` | 3개 모델 생성 |
| `apps/market_data/admin.py` | 새 Admin 등록 |
| `core/data/fetcher.py` | DB 조회 우선 로직, cache import 제거 |
| `core/data/cache.py` | 삭제 |
| `apps/market_data/api.py` | DB 기반 listing 조회 |
| `tests/` | DB mock으로 수정 |

## 설계 결정

- `fetcher.py`가 DB 접근 계층 겸임 (별도 repository 불필요)
- float 타입 사용 (기존 코드 일관성, 주가 정밀도 충분)
- 같은 테이블에 종목/지수 저장 (`is_index` 플래그 구분)
- 배치 메타는 범용 `BatchMeta` 테이블로 관리
