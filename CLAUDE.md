# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
uv run pytest tests/ -v

# Run a single test file
uv run pytest tests/test_backtest.py -v

# Run a specific test class or method
uv run pytest tests/test_backtest.py::TestDualMarketBacktest::test_dual_market_capital_split -v

# Launch Streamlit UI
uv run streamlit run src/ui/app.py
```

## Architecture

KOSPI + NASDAQ 이중 시장 알고리즘 거래 시뮬레이터. FinanceDataReader로 주가를 수집하고, 시그널 기반 백테스트 엔진으로 시뮬레이션한 뒤, Streamlit으로 결과를 시각화한다.

### Layer Structure

```
src/data/     → 외부 데이터 수집 (FinanceDataReader) + Parquet 캐시
src/engine/   → 시그널 감지, 포트폴리오 관리, 백테스트 엔진 (순수 로직)
src/ui/       → Streamlit 프레젠테이션 (sidebar, charts, tables)
```

### Core Design Decisions

- **시그널은 사전 계산**: `signals.py`의 함수들은 `pd.Series → pd.Series` 순수 함수. 백테스트 루프 진입 전에 모든 종목의 시그널을 한 번에 계산한다.
- **일별 루프 순서**: SELL → BUY → SNAPSHOT. 매도가 먼저 실행되어 확보된 현금으로 같은 날 매수 가능.
- **이중 시장 모델**: `run_backtest()`는 시장에 무관한 순수 시뮬레이션 함수. `run_dual_market_backtest()`가 자본 분할 → 독립 실행 → 환율 기반 합산을 오케스트레이팅한다. NASDAQ 포트폴리오는 USD 기준으로 운영되며, 합산 시 일별 USD/KRW 환율로 KRW 환산.
- **가격 데이터**: `dict[str, pd.DataFrame]` (종목코드 → OHLCV DataFrame, DatetimeIndex).

### Commit Convention

커밋 타입: `docs:`, `feat:`, `refactor:`, `fix:` (한국어 메시지). `/commit` 커맨드 사용 시 자동으로 목적별 분리 커밋.
