"""Differentiator demo: use SmartSelector to route through the cheapest
healthy upstream. Saves money without giving up reliability.

Install: pip install tierproxy httpx
"""

import httpx
from tierproxy import ProxyURL, TierProxy
from tierproxy.proxy.selector import SmartSelector


def main() -> None:
    client = TierProxy()
    selector = SmartSelector(client, strategy="cheapest", cache_ttl=30)

    for url in ["https://ipinfo.io/json", "https://api.ipify.org?format=json"]:
        chosen = selector.pick()
        print(
            f"Routing through {chosen.upstream_id} (cost ${chosen.cost_per_gb_usd}/GB, "
            f"p95 {chosen.latency_p95_ms}ms, success {chosen.success_rate:.1%})"
        )
        proxy = ProxyURL(
            api_key=client._transport.api_key,
            country="US",
            upstream_hint=chosen.upstream_id,
        )
        r = httpx.get(url, proxy=proxy.http_url(), headers=proxy.headers(), timeout=30)
        print(r.json())


if __name__ == "__main__":
    main()
