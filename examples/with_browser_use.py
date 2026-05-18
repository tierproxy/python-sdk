"""Browser-Use: autonomous browser controlled by an LLM, through tierproxy.

Lets the agent navigate, click, fill forms, and extract data. Crucial: the
proxy provides residential IPs that won't get instantly blocked by anti-bot
systems on big sites.

Install: pip install browser-use tierproxy langchain-openai && playwright install chromium
"""

import asyncio
import os

from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from langchain_openai import ChatOpenAI
from tierproxy import ProxyURL, TierProxy
from tierproxy.proxy.adapters import playwright_proxy_config


async def main() -> None:
    client = TierProxy()
    proxy = ProxyURL(
        api_key=os.environ["TIERPROXY_API_KEY"],
        country="US",
        session_id="browser-use-1",
        session_duration_minutes=20,
    )

    browser = Browser(
        config=BrowserConfig(
            headless=False,
            proxy=playwright_proxy_config(proxy),
        )
    )

    agent = Agent(
        task=(
            "Go to news.ycombinator.com, find the highest-voted story today, "
            "and return its title + URL as JSON."
        ),
        llm=ChatOpenAI(model="gpt-4o-mini"),
        browser=browser,
    )

    result = await agent.run()
    print(result)
    await browser.close()

    usage = client.usage.get()
    print(f"\nSession cost: ${usage.total_cost_usd:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
