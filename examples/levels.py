"""Single file that exercises Level-0 through Level-5 in sequence."""

import os

import tierproxy
from tierproxy import ProxyURL, TierProxy
from tierproxy.retry import RetryPolicy


def main() -> None:
    os.environ.setdefault("TIERPROXY_API_KEY", "tp_live_changeme")

    # ---- Level 0 ---------------------------------------------------------------
    print("--- Level 0 ---")
    print(tierproxy.get("https://ipinfo.io/json", country="US").json())

    # ---- Level 1 ---------------------------------------------------------------
    print("--- Level 1 ---")
    with TierProxy() as g:
        print("client_id =", g.me.get().client_id)
        print(g.get("https://ipinfo.io/json", country="GB").json())

    # ---- Level 2 ---------------------------------------------------------------
    print("--- Level 2 ---")
    with TierProxy(routing="cheapest") as g:
        print(g.get("https://ipinfo.io/json").json())

    # ---- Level 3 ---------------------------------------------------------------
    print("--- Level 3 ---")

    with TierProxy(
        monthly_budget_usd=200.0,
    ) as g:
        g.get("https://ipinfo.io/json")

    # ---- Level 4 ---------------------------------------------------------------
    print("--- Level 4 ---")
    with TierProxy(
        retry_policy=RetryPolicy(max_retries=5),
        user_agent_suffix="levels-demo/1.0",
    ) as g:
        g.get("https://ipinfo.io/json")

    # ---- Level 5 ---------------------------------------------------------------
    print("--- Level 5 ---")
    url = ProxyURL(
        api_key=os.environ["TIERPROXY_API_KEY"], country="US", mode="username_encoding"
    ).http_url()
    print("raw proxy URL:", url)


if __name__ == "__main__":
    main()
