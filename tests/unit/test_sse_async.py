"""Async SSE iterator coverage."""

from __future__ import annotations

import httpx
import pytest

from tierproxy._internal.sse import SSEEvent, aiter_sse


def _async_resp(lines: list[str]) -> httpx.Response:
    body = ("\n".join(lines) + "\n").encode()
    req = httpx.Request("GET", "http://x")
    return httpx.Response(200, content=body, request=req)


@pytest.mark.asyncio
async def test_aiter_sse_basic_event() -> None:
    resp = _async_resp(
        [
            "event: usage_delta",
            'data: {"x":1}',
            "",
        ]
    )
    events = [e async for e in aiter_sse(resp)]
    assert events == [SSEEvent(event="usage_delta", data='{"x":1}', id=None)]


@pytest.mark.asyncio
async def test_aiter_sse_comment_and_no_field_colon() -> None:
    resp = _async_resp([": keep", "data", "data: y", ""])
    events = [e async for e in aiter_sse(resp)]
    assert events[0].data == "\ny"
