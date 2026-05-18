"""Shared httpx-based transport. Both sync and async clients call into this."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, cast

import httpx

from tierproxy._version import __version__
from tierproxy.errors import (
    ConnectionError as GwConnectionError,
)
from tierproxy.errors import (
    TimeoutError as GwTimeoutError,
)
from tierproxy.errors import (
    from_problem,
)
from tierproxy.observability.redact import redact_headers, redact_url
from tierproxy.retry import RetryPolicy

# Any future debug/error log that includes headers or URLs MUST route them
# through redact_headers / redact_url first — see tierproxy.observability.redact.
_ = (redact_headers, redact_url)

log = logging.getLogger("tierproxy")
_DEFAULT_UA = f"tierproxy-python/{__version__} httpx/{httpx.__version__}"


class Transport:
    """Backs both TierProxy and AsyncTierProxy."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float,
        retry: RetryPolicy,
        ua_suffix: str | None,
        http_client: httpx.Client | httpx.AsyncClient | None,
        is_async: bool,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.retry = retry
        self.ua = f"{_DEFAULT_UA} {ua_suffix}".strip() if ua_suffix else _DEFAULT_UA
        self._is_async = is_async
        self._client: httpx.Client | httpx.AsyncClient
        if http_client is not None:
            self._client = http_client
        elif is_async:
            self._client = httpx.AsyncClient(timeout=timeout)
        else:
            self._client = httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": self.ua,
            "Accept": "application/json",
        }

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert not self._is_async
        return self._dispatch_sync(method, path, **kwargs)

    async def arequest(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert self._is_async
        return await self._dispatch_async(method, path, **kwargs)

    def _dispatch_sync(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        client = cast(httpx.Client, self._client)
        attempt = 0
        while True:
            try:
                resp = client.request(
                    method,
                    self.base_url + path,
                    headers=self._headers(),
                    **kwargs,
                )
            except (httpx.ConnectError, httpx.NetworkError) as e:
                if self.retry.should_retry(attempt, method, None, True, True):
                    time.sleep(self.retry.delay(attempt))
                    attempt += 1
                    continue
                raise GwConnectionError(str(e)) from e
            except httpx.TimeoutException as e:
                if self.retry.should_retry(attempt, method, 408, False, True):
                    time.sleep(self.retry.delay(attempt))
                    attempt += 1
                    continue
                raise GwTimeoutError(str(e)) from e
            if 200 <= resp.status_code < 300:
                if resp.headers.get("Content-Type", "").startswith("text/event-stream"):
                    return {"_sse_response": resp}
                return cast(dict[str, Any], resp.json()) if resp.content else {}
            if self.retry.should_retry(attempt, method, resp.status_code, False, True):
                retry_after = float(resp.headers.get("Retry-After", "0")) or None
                time.sleep(self.retry.delay(attempt, retry_after))
                attempt += 1
                continue
            self._raise_for(resp)

    async def _dispatch_async(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        client = cast(httpx.AsyncClient, self._client)
        attempt = 0
        while True:
            try:
                resp = await client.request(
                    method,
                    self.base_url + path,
                    headers=self._headers(),
                    **kwargs,
                )
            except (httpx.ConnectError, httpx.NetworkError) as e:
                if self.retry.should_retry(attempt, method, None, True, True):
                    await asyncio.sleep(self.retry.delay(attempt))
                    attempt += 1
                    continue
                raise GwConnectionError(str(e)) from e
            except httpx.TimeoutException as e:
                if self.retry.should_retry(attempt, method, 408, False, True):
                    await asyncio.sleep(self.retry.delay(attempt))
                    attempt += 1
                    continue
                raise GwTimeoutError(str(e)) from e
            if 200 <= resp.status_code < 300:
                if resp.headers.get("Content-Type", "").startswith("text/event-stream"):
                    return {"_sse_response": resp}
                return cast(dict[str, Any], resp.json()) if resp.content else {}
            if self.retry.should_retry(attempt, method, resp.status_code, False, True):
                retry_after = float(resp.headers.get("Retry-After", "0")) or None
                await asyncio.sleep(self.retry.delay(attempt, retry_after))
                attempt += 1
                continue
            self._raise_for(resp)

    @staticmethod
    def _raise_for(resp: httpx.Response) -> None:
        try:
            problem = resp.json()
        except Exception:  # noqa: BLE001
            problem = {
                "title": resp.text or "error",
                "request_id": resp.headers.get("X-Request-Id"),
            }
        raise from_problem(resp.status_code, problem)
