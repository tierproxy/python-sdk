import pytest
from pytest_httpx import HTTPXMock

from tierproxy import AsyncTierProxy, TierProxy


def test_stream_true_returns_streaming_context_manager(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://example.com/big",
        content=b"chunk-1\nchunk-2\nchunk-3\n",
    )
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")

    chunks: list[bytes] = []
    with client.get("https://example.com/big", stream=True) as resp:
        assert resp.status_code == 200
        for chunk in resp.iter_bytes():
            chunks.append(chunk)

    body = b"".join(chunks)
    assert body == b"chunk-1\nchunk-2\nchunk-3\n"


def test_non_streaming_still_returns_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://example.com/normal", json={"ok": True})
    client = TierProxy(api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444")

    resp = client.get("https://example.com/normal")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_async_stream_true_returns_streaming_context_manager(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://example.com/big",
        content=b"a\nb\nc\n",
    )
    async with AsyncTierProxy(
        api_key="tp_test_DUMMY_1234567890ABCDEF", base_url="https://gw.local:8444"
    ) as g:
        cm = await g.get("https://example.com/big", stream=True)
        chunks: list[bytes] = []
        async with cm as resp:
            assert resp.status_code == 200
            async for chunk in resp.aiter_bytes():
                chunks.append(chunk)
        assert b"".join(chunks) == b"a\nb\nc\n"
