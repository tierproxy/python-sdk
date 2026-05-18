"""Crawl4AI (Playwright under the hood) - uses username-encoded modifiers
because Playwright's proxy config ignores headers on CONNECT.

Install: pip install crawl4ai tierproxy
"""

import asyncio

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from tierproxy import AsyncTierProxy, ProxyURL
from tierproxy.proxy.adapters import playwright_proxy_config


async def main():
    client = AsyncTierProxy()
    proxy = ProxyURL(
        api_key=client._transport.api_key,
        country="US",
        session_id="crawl4ai-batch",
        session_duration_minutes=30,
    )
    browser = BrowserConfig(proxy_config=playwright_proxy_config(proxy))
    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun("https://example.com", config=CrawlerRunConfig())
        print(result.markdown[:500])


if __name__ == "__main__":
    asyncio.run(main())
