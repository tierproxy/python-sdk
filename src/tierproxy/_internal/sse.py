"""Minimal Server-Sent Events parser. Yields dataclasses, no buffering hell."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any, cast

import httpx


@dataclass
class SSEEvent:
    event: str
    data: str
    id: str | None = None


def _flush(state: dict[str, Any]) -> SSEEvent | None:
    data_lines = cast(list[str], state.get("data") or [])
    if not data_lines:
        return None
    return SSEEvent(
        event=cast(str, state.get("event") or "message"),
        data="\n".join(data_lines),
        id=cast("str | None", state.get("id")),
    )


def iter_sse(resp: httpx.Response) -> Iterator[SSEEvent]:
    state: dict[str, Any] = {"data": []}
    for raw in resp.iter_lines():
        if raw == "":
            ev = _flush(state)
            if ev:
                yield ev
            state = {"data": []}
            continue
        if raw.startswith(":"):
            continue
        if ":" in raw:
            field, _, value = raw.partition(":")
            value = value.lstrip(" ")
        else:
            field, value = raw, ""
        if field == "data":
            state.setdefault("data", []).append(value)
        elif field in {"event", "id"}:
            state[field] = value


async def aiter_sse(resp: httpx.Response) -> AsyncIterator[SSEEvent]:
    state: dict[str, Any] = {"data": []}
    async for raw in resp.aiter_lines():
        if raw == "":
            ev = _flush(state)
            if ev:
                yield ev
            state = {"data": []}
            continue
        if raw.startswith(":"):
            continue
        if ":" in raw:
            field, _, value = raw.partition(":")
            value = value.lstrip(" ")
        else:
            field, value = raw, ""
        if field == "data":
            state.setdefault("data", []).append(value)
        elif field in {"event", "id"}:
            state[field] = value
