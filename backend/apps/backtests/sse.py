"""SSE (Server-Sent Events) 포맷 유틸리티."""

import json


def format_sse(event_type: str, data: dict) -> str:
    """SSE 이벤트 문자열을 생성한다.

    Args:
        event_type: 이벤트 타입 (phase, progress, trade, result, error)
        data: JSON 직렬화할 데이터 딕셔너리

    Returns:
        SSE 포맷 문자열 ("event: ...\ndata: ...\n\n")
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"
