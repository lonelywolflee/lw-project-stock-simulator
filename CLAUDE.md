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

## Rules Structure

각 레이어의 상세 개발 가이드는 `.claude/rules/` 하위에 분리되어 있다:

| 파일 | 대상 레이어 | 주요 내용 |
|------|------------|-----------|
| `.claude/rules/data.md` | `src/data/` | FinanceDataReader 래퍼, Parquet 캐시, 가격 데이터 형식 |
| `.claude/rules/engine.md` | `src/engine/` | 시그널 사전 계산, 일별 루프 순서, 이중 시장 모델, 매매 알고리즘 |
| `.claude/rules/ui.md` | `src/ui/` | Streamlit 오케스트레이션, 사이드바, Plotly 차트, 테이블 |

### Commit Convention

커밋 타입: `docs:`, `feat:`, `refactor:`, `fix:` (한국어 메시지). `/commit` 커맨드 사용 시 자동으로 목적별 분리 커밋.
