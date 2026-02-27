"""SSE (Server-Sent Events) 포맷 유틸리티."""

import json

import numpy as np


class _NumpyEncoder(json.JSONEncoder):
    """numpy 타입을 Python 네이티브 타입으로 변환하는 JSON 인코더."""

    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


def format_sse(event_type: str, data: dict) -> str:
    """SSE 이벤트 문자열을 생성한다.

    Args:
        event_type: 이벤트 타입 (phase, progress, trade, result, error)
        data: JSON 직렬화할 데이터 딕셔너리

    Returns:
        SSE 포맷 문자열 ("event: ...\ndata: ...\n\n")
    """
    payload = json.dumps(data, ensure_ascii=False, cls=_NumpyEncoder)
    return f"event: {event_type}\ndata: {payload}\n\n"
