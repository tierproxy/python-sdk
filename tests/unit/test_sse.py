import httpx

from tierproxy._internal.sse import SSEEvent, iter_sse


def _resp_with_lines(lines: list[str]) -> httpx.Response:
    body = ("\n".join(lines) + "\n").encode()
    req = httpx.Request("GET", "http://x")
    return httpx.Response(200, content=body, request=req)


def test_basic_event() -> None:
    resp = _resp_with_lines(
        [
            "event: usage_delta",
            'data: {"x":1}',
            "",
        ]
    )
    events = list(iter_sse(resp))
    assert events == [SSEEvent(event="usage_delta", data='{"x":1}', id=None)]


def test_multi_line_data() -> None:
    resp = _resp_with_lines(
        [
            "event: x",
            "data: line1",
            "data: line2",
            "",
        ]
    )
    events = list(iter_sse(resp))
    assert events[0].data == "line1\nline2"


def test_default_event_name_is_message() -> None:
    resp = _resp_with_lines(["data: hi", ""])
    events = list(iter_sse(resp))
    assert events[0].event == "message"


def test_comment_line_ignored() -> None:
    resp = _resp_with_lines([": keepalive", "event: x", "data: y", ""])
    events = list(iter_sse(resp))
    assert events[0].event == "x"
