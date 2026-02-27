"""Parquet 파일 기반 로컬 캐시 모듈."""

from pathlib import Path

import pandas as pd

CACHE_DIR = Path(".cache")


def get_cache_path(code: str, start: str, end: str) -> Path:
    """캐시 파일 경로를 반환한다."""
    return CACHE_DIR / f"{code}_{start}_{end}.parquet"


def load_from_cache(code: str, start: str, end: str) -> pd.DataFrame | None:
    """캐시 파일이 존재하면 DataFrame을 반환, 없으면 None."""
    path = get_cache_path(code, start, end)
    if path.exists():
        return pd.read_parquet(path)
    return None


def save_to_cache(code: str, start: str, end: str, df: pd.DataFrame) -> None:
    """DataFrame을 Parquet 파일로 캐시에 저장한다."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = get_cache_path(code, start, end)
    df.to_parquet(path)
