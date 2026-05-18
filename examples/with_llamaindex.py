"""LlamaIndex SimpleWebPageReader through the proxy.

Install: pip install llama-index-readers-web httpx tierproxy
"""

import httpx
from llama_index.readers.web import SimpleWebPageReader
from tierproxy import ProxyURL, TierProxy

client = TierProxy()
proxy = ProxyURL(api_key=client._transport.api_key, country="US")
http = httpx.Client(proxy=proxy.http_url(), headers=proxy.headers(), timeout=60)

reader = SimpleWebPageReader(html_to_text=True, http_client=http)
docs = reader.load_data(urls=["https://example.com/article"])
for d in docs:
    print(d.text[:200])
