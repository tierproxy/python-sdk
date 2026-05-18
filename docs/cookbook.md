# Cookbook — recipes

Each recipe is copy-paste runnable. Set `TIERPROXY_API_KEY` first.

## 1. Scrape a news site through residential IPs

```python
import tierproxy
r = tierproxy.get("https://news.ycombinator.com", country="US")
print(r.text[:2000])
```

## 2. RAG ingestion through tierproxy (LangChain)

```python
from langchain_community.document_loaders import WebBaseLoader
from tierproxy import TierProxy, ProxyURL
import os

client = TierProxy()
proxy = ProxyURL(api_key=os.environ["TIERPROXY_API_KEY"], country="US")
loader = WebBaseLoader(
    web_paths=["https://example.com/article1", "https://example.com/article2"],
    proxies={"http": proxy.http_url(), "https": proxy.http_url()},
    header_template=proxy.headers(),
)
docs = loader.load()
print(f"Loaded {len(docs)} docs")
```

## 3. Playwright browser through tierproxy

```python
from playwright.sync_api import sync_playwright
from tierproxy import TierProxy, ProxyURL
from tierproxy.proxy.adapters import playwright_proxy_config

client = TierProxy()
proxy = ProxyURL(api_key=client._transport.api_key, country="US", mode="username_encoding")

with sync_playwright() as p:
    browser = p.chromium.launch(proxy=playwright_proxy_config(proxy))
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
```

## 4. Live cost dashboard (terminal)

```python
from tierproxy import TierProxy

with TierProxy() as g:
    for delta in g.usage.stream():
        cost_per_gb = 4.0  # use g.health.upstreams() for real-time per-upstream cost
        cost = delta.total_bytes / 1024**3 * cost_per_gb
        print(f"\r{delta.ts}  {delta.total_bytes:>15,} bytes  ${cost:.2f} mtd", end="")
```

## 5. MCP integration (Claude Desktop / Cursor / Cline / Windsurf)

```bash
pip install tierproxy[mcp]
```

Then in your MCP client config:

```json
{
  "mcpServers": {
    "tierproxy": {
      "command": "tierproxy-mcp",
      "env": { "TIERPROXY_API_KEY": "tp_live_..." }
    }
  }
}
```

Now your AI assistant can call `fetch_url(url, country="US")` natively.
