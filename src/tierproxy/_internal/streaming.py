"""Stream-mode helpers.

``is_stream`` pops the ``stream`` kwarg from a request kwargs dict and reports
whether streaming was requested. Streaming responses bypass the response cache
and the failover wrapper (both assume a fully-read ``httpx.Response``).

Callers receive a context manager and own its lifecycle:

    with client.get(url, stream=True) as resp:
        for chunk in resp.iter_bytes():
            ...

Streaming + per-session cookie persistence are mutually exclusive in this
iteration: the response body is not buffered, so post-flight cookie merge
would race with caller iteration.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterator


def is_stream(kwargs: dict[str, Any]) -> bool:
    return bool(kwargs.pop("stream", False))


@contextmanager
def sync_stream(
    method: str,
    url: str,
    *,
    proxy: str,
    timeout: float,
    headers: dict[str, str],
    **kwargs: Any,
) -> Iterator[httpx.Response]:
    """Open a streamed httpx request and close the underlying client on exit."""
    client = httpx.Client(proxy=proxy, timeout=timeout)
    try:
        with client.stream(method, url, headers=headers, **kwargs) as resp:
            yield resp
    finally:
        client.close()


class AsyncStreamCM:
    """`async with` wrapper that owns both the AsyncClient and the stream cm."""

    def __init__(
        self,
        method: str,
        url: str,
        *,
        proxy: str,
        timeout: float,
        headers: dict[str, str],
        **kwargs: Any,
    ) -> None:
        self._method = method
        self._url = url
        self._proxy = proxy
        self._timeout = timeout
        self._headers = headers
        self._kwargs = kwargs
        self._client: httpx.AsyncClient | None = None
        self._stream_cm: Any = None

    async def __aenter__(self) -> httpx.Response:
        self._client = httpx.AsyncClient(proxy=self._proxy, timeout=self._timeout)
        self._stream_cm = self._client.stream(
            self._method, self._url, headers=self._headers, **self._kwargs
        )
        resp: httpx.Response = await self._stream_cm.__aenter__()
        return resp

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            if self._stream_cm is not None:
                await self._stream_cm.__aexit__(exc_type, exc, tb)
        finally:
            if self._client is not None:
                await self._client.aclose()
