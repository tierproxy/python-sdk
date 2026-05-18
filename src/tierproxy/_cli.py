"""`tierproxy` CLI - minimum-viable for users who want curl-style ergonomics.

Usage:
    tierproxy doctor                       # verify auth + show health snapshot
    tierproxy usage                        # current month usage + cost
"""

from __future__ import annotations

import argparse
import sys


def cmd_doctor(args: argparse.Namespace) -> int:
    from tierproxy import TierProxy

    g = TierProxy(api_key=args.api_key)
    me = g.me.get()
    print(
        f"OK Auth - client {me.client_id} ({me.plan_id}), "
        f"{me.used_bytes_month:,}/{me.quota_bytes_month:,} bytes used"
    )
    ups = g.health.upstreams()
    print(f"OK Upstreams ({len(ups)}):")
    for u in ups:
        print(
            f"  - {u.upstream_id:14} state={u.state}  cb={u.cb_state}  "
            f"sr={u.success_rate:.1%}  p95={u.latency_p95_ms}ms  "
            f"${u.cost_per_gb_usd}/GB"
        )
    return 0


def cmd_usage(args: argparse.Namespace) -> int:
    from tierproxy import TierProxy

    g = TierProxy(api_key=args.api_key)
    u = g.usage.get()
    print(f"Period: {u.from_} -> {u.to}")
    print(f"Total: {u.total_bytes:,} bytes  /  ${u.total_cost_usd:.2f}")
    for d in u.days:
        print(f"  {d.date}  up={d.bytes_up:,}  down={d.bytes_down:,}  ${d.cost_usd:.4f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tierproxy")
    p.add_argument("--api-key", help="defaults to TIERPROXY_API_KEY env var")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="verify auth + show upstream health").set_defaults(
        func=cmd_doctor
    )

    sub.add_parser("usage", help="show current-month usage + cost").set_defaults(func=cmd_usage)

    args = p.parse_args(argv)
    func = args.func
    return int(func(args))


if __name__ == "__main__":
    sys.exit(main())
