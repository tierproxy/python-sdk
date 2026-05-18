"""Firecrawl + tierproxy: cheap LLM-ready scraping through residential proxies.

Firecrawl's default scraper hits the target directly from its servers; using
tierproxy as the HTTP backend gives you geo-targeting + sticky sessions +
residential IPs at a fraction of their managed-service cost.

Install: pip install firecrawl-py tierproxy
"""

import os

import requests
from firecrawl import FirecrawlApp
from tierproxy import ProxyURL, TierProxy

client = TierProxy()
proxy = ProxyURL(
    api_key=os.environ["TIERPROXY_API_KEY"],
    country="US",
    session_id="firecrawl-batch-1",
    session_duration_minutes=30,
)

# Firecrawl >= 0.0.18 accepts a custom requests.Session via session=
session = requests.Session()
session.proxies.update({"http": proxy.http_url(), "https": proxy.http_url()})
session.headers.update(proxy.headers())

app = FirecrawlApp(api_key="self-hosted-or-empty", session=session)
result = app.scrape_url(
    "https://news.ycombinator.com",
    params={"formats": ["markdown", "links"]},
)
print(result["markdown"][:1000])

me = client.me.get()
print(f"\nAccount {me.client_id}: {me.remaining_bytes:,} bytes remaining")
