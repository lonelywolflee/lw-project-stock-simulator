# KOSPI + NASDAQ 이중 시장 알고리즘 거래 시뮬레이터

FinanceDataReader로 KOSPI/NASDAQ 과거 데이터를 수집하고, 시그널 기반 백테스트 엔진으로 매매 전략을 시뮬레이션한 뒤, Streamlit 대시보드로 결과를 시각화하는 로컬 기반 증권 거래 시뮬레이터.

## 기술 스택

- **Python** 3.12+ (패키지 관리: uv)
- **FinanceDataReader** — 주가, 지수, 환율 데이터 수집
- **Pandas / NumPy** — 데이터 분석 및 시뮬레이션 로직
- **Streamlit** — 인터랙티브 웹 UI
- **Plotly** — 수익률 및 자산 변동 그래프 시각화
- **PyArrow** — Parquet 캐시 I/O

## 주요 기능

### 매매 알고리즘

- **매수**: n일 연속 상승 종목을 시가총액 또는 수익률 순으로 정렬하여 종목당 최대 금액까지 매수
- **매도**: m일 연속 하락 시 전량 매도, 당일 y% 이상 급락 시 긴급 손절
- **수수료**: 매수/매도 시 k% 차감

### 이중 시장 지원

- KOSPI/NASDAQ 비율 조절 가능 (0~100%)
- NASDAQ 포트폴리오는 USD 기준 운영, 합산 시 일별 환율로 KRW 환산

### 시각화

- 자산 추이 영역 차트 (현금 + 주식 평가액)
- 포트폴리오 vs KOSPI/NASDAQ 벤치마크 수익률 비교
- 핵심 지표 카드 (수익률, MDD, 거래수, 승률, 수수료)
- 거래 내역 테이블

## 실행 방법

```bash
# UI 실행
uv run streamlit run src/ui/app.py

# 전체 테스트
uv run pytest tests/ -v
```

## 프로젝트 구조

```
src/
├── data/       # 외부 데이터 수집 (FinanceDataReader) + Parquet 캐시
│   ├── fetcher.py
│   └── cache.py
├── engine/     # 시그널 감지, 포트폴리오 관리, 백테스트 엔진 (순수 로직)
│   ├── signals.py
│   ├── portfolio.py
│   └── backtest.py
└── ui/         # Streamlit 프레젠테이션
    ├── app.py
    ├── sidebar.py
    ├── charts.py
    └── tables.py
tests/          # pytest 기반 단위 테스트
```
