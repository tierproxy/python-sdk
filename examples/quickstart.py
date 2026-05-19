"""Minimal sync example. Prints account info + uses the proxy with httpx."""

import httpx
from tierproxy import ProxyURL, TierProxy


def main() -> None:
    with TierProxy() as client:  # uses TIERPROXY_API_KEY
        me = client.me.get()
        print(
            f"Account {me.client_id} | used {me.used_bytes_month:,} / {me.quota_bytes_month:,} bytes"
        )

        proxy = ProxyURL(api_key=client._transport.api_key, country="US", session_id="quickstart-1")
        r = httpx.get(
            "https://ipinfo.io", proxy=proxy.http_url(), headers=proxy.headers(), timeout=30
        )
        print("Exit IP info:", r.json())


if __name__ == "__main__":
    main()
