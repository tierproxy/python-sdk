"""Async variant. Same flow with asyncio + httpx.AsyncClient."""

import asyncio

import httpx
from tierproxy import AsyncTierProxy, ProxyURL


async def main():
    async with AsyncTierProxy() as client:
        me = await client.me.get()
        print(f"Async account {me.client_id}")

        proxy = ProxyURL(api_key=client._transport.api_key, country="GB")
        async with httpx.AsyncClient(proxy=proxy.http_url(), headers=proxy.headers()) as h:
            r = await h.get("https://ipinfo.io")
            print(r.json())


if __name__ == "__main__":
    asyncio.run(main())
