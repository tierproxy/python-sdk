"""Direct Playwright. Sync API.

Install: pip install playwright tierproxy && playwright install chromium
"""

from playwright.sync_api import sync_playwright
from tierproxy import ProxyURL, TierProxy
from tierproxy.proxy.adapters import playwright_proxy_config

client = TierProxy()
proxy = ProxyURL(api_key=client._transport.api_key, country="US")
cfg = playwright_proxy_config(proxy)

with sync_playwright() as p:
    browser = p.chromium.launch(proxy=cfg, headless=True)
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
