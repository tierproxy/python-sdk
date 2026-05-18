import pytest

mcp = pytest.importorskip("mcp")


@pytest.mark.asyncio
async def test_build_server_registers_4_tools() -> None:
    from tierproxy.mcp.server import build_server

    server = build_server(api_key="tp_test_DUMMY_1234567890ABCDEF")
    assert server.name == "tierproxy"


@pytest.mark.asyncio
async def test_main_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TIERPROXY_API_KEY", raising=False)
    from tierproxy.mcp.server import main

    assert main() == 1
