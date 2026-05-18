"""Differentiator demo: tail live usage via SSE. Pair with a cost-alarm callback."""

from tierproxy import TierProxy

client = TierProxy()
print("Tailing usage. Ctrl-C to stop.")
for delta in client.usage.stream():
    print(f"[{delta.ts}] total {delta.total_bytes:,} bytes  (+{delta.delta_bytes:,} since last)")
    if delta.delta_bytes > 100 * 1024 * 1024:  # >100 MB in 5s
        print("WARN: surge detected")
