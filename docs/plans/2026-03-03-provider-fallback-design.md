# 데이터 Provider 이중화 설계

## 문제

FinanceDataReader(FDR)가 외부 서비스 장애로 조회 실패할 수 있다.
단일 소스 의존은 백테스트 실행을 불가능하게 만든다.

## 목표

FDR 실패 시 pykrx로 자동 fallback하여 데이터 수집 안정성을 높인다.

## 설계

### Provider 구조

```
core/data/
├── fetcher.py              (provider 조합 + retry/fallback)
└── providers/
    ├── __init__.py          (공통 인터페이스 정의)
    ├── fdr_provider.py      (FinanceDataReader)
    └── pykrx_provider.py    (pykrx)
```

### Provider 인터페이스

각 provider는 동일한 함수 시그니처를 구현한다:

```python
# stock_listing(market: str) -> pd.DataFrame
#   columns: ["Code", "Name", "Marcap"]

# price_data(code: str, start: str, end: str) -> pd.DataFrame
#   index: DatetimeIndex, columns: ["Open", "High", "Low", "Close", "Volume"]
```

### pykrx Provider 변환 책임

| 항목 | pykrx raw | 변환 후 |
|------|-----------|---------|
| 컬럼명 | 시가, 고가, 저가, 종가, 거래량 | Open, High, Low, Close, Volume |
| 날짜 입력 | "20240102" | "2024-01-02"에서 변환 |
| 종목 목록 | ticker 리스트 + get_market_ticker_name | DataFrame(Code, Name, Marcap) |

### Fallback 흐름

```
fetcher 함수 호출
  → FDR provider 시도 (3회 재시도)
  → 실패 시 pykrx provider 시도 (3회 재시도)
  → 둘 다 실패 시 예외
```

### 변경 파일

| 파일 | 변경 |
|------|------|
| `core/data/providers/__init__.py` | 신규: 인터페이스 정의 |
| `core/data/providers/fdr_provider.py` | 신규: FDR 래핑 |
| `core/data/providers/pykrx_provider.py` | 신규: pykrx 래핑 + 컬럼/날짜 변환 |
| `core/data/fetcher.py` | 수정: provider 기반 fallback 로직 |
| `backend/pyproject.toml` | 수정: pykrx 의존성 추가 |
| `tests/test_fetcher.py` | 수정: provider mock 기반 테스트 |

### 설계 결정

- provider는 순수 함수 모듈 (클래스 아님) — 기존 코드 스타일과 일관
- 변환 책임은 각 provider 내부 — fetcher는 provider를 몰라도 됨
- pykrx는 KRX 스크래핑이므로 요청 간 1초 대기 권장
