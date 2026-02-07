"""매수/매도 시그널 감지 모듈 - 순수 함수 기반."""

import pandas as pd


def detect_consecutive_rises(close_series: pd.Series, n: int) -> pd.Series:
    """n일 연속 종가 상승을 감지한다.

    Args:
        close_series: 종가 시리즈 (날짜 인덱스)
        n: 연속 상승 일수

    Returns:
        bool Series - True인 날짜에 매수 시그널 발생
    """
    rising = (close_series.diff() > 0).astype(int)
    return rising.rolling(window=n, min_periods=n).sum() == n


def detect_consecutive_falls(close_series: pd.Series, m: int) -> pd.Series:
    """m일 연속 종가 하락을 감지한다.

    Args:
        close_series: 종가 시리즈 (날짜 인덱스)
        m: 연속 하락 일수

    Returns:
        bool Series - True인 날짜에 매도 시그널 발생
    """
    falling = (close_series.diff() < 0).astype(int)
    return falling.rolling(window=m, min_periods=m).sum() == m


def detect_emergency_sell(close_series: pd.Series, y_pct: float) -> pd.Series:
    """당일 종가가 전일 대비 y% 이상 급락한 경우를 감지한다.

    Args:
        close_series: 종가 시리즈 (날짜 인덱스)
        y_pct: 급락 기준 비율 (예: 5.0은 5%)

    Returns:
        bool Series - True인 날짜에 긴급 매도 시그널 발생
    """
    pct_change = close_series.pct_change() * 100
    return pct_change <= -y_pct
