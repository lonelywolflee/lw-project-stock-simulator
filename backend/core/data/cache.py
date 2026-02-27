"""Parquet 파일 기반 로컬 캐시 모듈.

사용자별 디렉토리로 분리하고, 종목당 1개 파일만 유지한다.
"""

from pathlib import Path

import pandas as pd

CACHE_DIR = Path(".cache")


def _user_dir(username: str) -> Path:
    """사용자별 캐시 디렉토리 경로를 반환한다."""
    return CACHE_DIR / username


def load_from_cache(username: str, code: str, start: str, end: str) -> pd.DataFrame | None:
    """캐시 파일이 존재하면 DataFrame을 반환, 없으면 None."""
    path = _user_dir(username) / f"{code}_{start}_{end}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None


def save_to_cache(username: str, code: str, start: str, end: str, df: pd.DataFrame) -> None:
    """DataFrame을 Parquet 파일로 캐시에 저장한다.

    동일 종목의 기존 캐시 파일이 있으면 삭제하고 새로 저장한다.
    """
    user_dir = _user_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)

    # 동일 종목의 이전 캐시 삭제 (종목당 1개만 유지)
    for old_file in user_dir.glob(f"{code}_*.parquet"):
        old_file.unlink()

    path = user_dir / f"{code}_{start}_{end}.parquet"
    df.to_parquet(path)
