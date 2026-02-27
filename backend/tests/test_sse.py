"""SSE 포맷 유틸리티 테스트."""

from apps.backtests.sse import format_sse


class TestFormatSSE:
    def test_basic_event(self):
        result = format_sse("phase", {"phase": 1, "message": "로딩 중..."})
        assert "event: phase\n" in result
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_event_contains_double_newline(self):
        """SSE 이벤트는 반드시 \\n\\n 으로 끝나야 한다."""
        result = format_sse("progress", {"current": 1, "total": 10})
        assert result.endswith("\n\n")

    def test_event_has_correct_prefix(self):
        result = format_sse("trade", {"side": "BUY"})
        lines = result.strip().split("\n")
        assert lines[0] == "event: trade"
        assert lines[1].startswith("data: ")

    def test_data_is_valid_json(self):
        import json

        result = format_sse("result", {"value": 42})
        data_line = result.strip().split("\n")[1]
        payload = data_line[len("data: ") :]
        parsed = json.loads(payload)
        assert parsed == {"value": 42}
