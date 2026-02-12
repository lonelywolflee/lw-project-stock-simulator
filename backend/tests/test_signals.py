"""시그널 감지 로직 테스트 - 합성 데이터 기반."""

import pandas as pd
import pytest

from core.engine.signals import (
    detect_consecutive_falls,
    detect_consecutive_rises,
    detect_emergency_sell,
)


def _make_series(values: list[float]) -> pd.Series:
    """테스트용 종가 시리즈를 생성한다."""
    dates = pd.date_range("2024-01-01", periods=len(values), freq="B")
    return pd.Series(values, index=dates, name="Close")


class TestConsecutiveRises:
    def test_exact_n_days(self):
        # 3일 연속 상승: 100→101→102→103
        close = _make_series([100, 101, 102, 103, 100])
        result = detect_consecutive_rises(close, n=3)
        # 인덱스 3 (4번째 값)에서 True
        assert result.iloc[3] == True
        assert result.iloc[4] == False

    def test_no_signal_when_short(self):
        # 2일 연속 상승만 있으면 n=3 시그널 없음
        close = _make_series([100, 101, 102, 100, 99])
        result = detect_consecutive_rises(close, n=3)
        assert not result.any()

    def test_continuous_rise(self):
        # 5일 연속 상승 → n=3일 때 인덱스 3, 4, 5에서 True
        close = _make_series([100, 101, 102, 103, 104, 105])
        result = detect_consecutive_rises(close, n=3)
        assert result.iloc[3] == True
        assert result.iloc[4] == True
        assert result.iloc[5] == True

    def test_flat_days_no_signal(self):
        # 보합은 상승이 아님
        close = _make_series([100, 100, 100, 100])
        result = detect_consecutive_rises(close, n=2)
        assert not result.any()


class TestConsecutiveFalls:
    def test_exact_m_days(self):
        # 3일 연속 하락: 103→102→101→100
        close = _make_series([103, 102, 101, 100, 105])
        result = detect_consecutive_falls(close, m=3)
        assert result.iloc[3] == True
        assert result.iloc[4] == False

    def test_no_signal_when_short(self):
        close = _make_series([103, 102, 101, 105, 106])
        result = detect_consecutive_falls(close, m=3)
        assert not result.any()


class TestEmergencySell:
    def test_large_drop(self):
        # 100 → 90 = -10% 하락
        close = _make_series([100, 90])
        result = detect_emergency_sell(close, y_pct=5.0)
        assert result.iloc[1] == True

    def test_small_drop_no_signal(self):
        # 100 → 97 = -3% 하락 (5% 미달)
        close = _make_series([100, 97])
        result = detect_emergency_sell(close, y_pct=5.0)
        assert result.iloc[1] == False

    def test_exact_threshold(self):
        # 100 → 95 = 정확히 -5%
        close = _make_series([100, 95])
        result = detect_emergency_sell(close, y_pct=5.0)
        assert result.iloc[1] == True
