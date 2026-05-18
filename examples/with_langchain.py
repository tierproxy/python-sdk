"""LangChain WebBaseLoader -> vector store, scraping through the proxy.

Install: pip install langchain-community beautifulsoup4 tierproxy
"""

import os

from langchain_community.document_loaders import WebBaseLoader
from tierproxy import ProxyURL, TierProxy

client = TierProxy()
me = client.me.get()
print(f"Account {me.client_id}, {me.remaining_bytes:,} bytes remaining this month")

proxy = ProxyURL(
    api_key=os.environ["TIERPROXY_API_KEY"],
    country="US",
    session_id="langchain-rag",
    session_duration_minutes=30,
)

loader = WebBaseLoader(
    web_paths=[
        "https://example.com/post1",
        "https://example.com/post2",
    ],
    proxies={"http": proxy.http_url(), "https": proxy.http_url()},
    header_template=proxy.headers(),  # honored by underlying urllib
)
documents = loader.load()
print(f"Loaded {len(documents)} docs via tierproxy")
