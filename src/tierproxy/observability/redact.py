"""Header + URL redaction for log lines.

Internal helper used by every SDK log/error path so secrets never reach
stdout, logging handlers, or trace exporters. Single source of truth.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

SENSITIVE_HEADERS = frozenset({"authorization", "proxy-authorization", "x-api-key", "cookie"})
_SCHEME_PREFIX_HEADERS = frozenset({"authorization", "proxy-authorization"})


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive values masked.

    For `Authorization` / `Proxy-Authorization`, the scheme prefix
    (`Bearer`, `Basic`) is preserved so the redacted value is still
    recognizable for debugging. Other sensitive headers collapse to `***`.
    """
    out: dict[str, str] = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in SENSITIVE_HEADERS:
            if lk in _SCHEME_PREFIX_HEADERS:
                scheme, sep, _ = v.partition(" ")
                out[k] = f"{scheme} ***" if sep else "***"
            else:
                out[k] = "***"
        else:
            out[k] = v
    return out


def redact_url(url: str) -> str:
    """Return URL with any userinfo (`user:pass@`) masked.

    Useful when the SDK logs the full proxy URL — credentials embedded in
    the username portion get replaced with `***:***`.
    """
    parts = urlsplit(url)
    if not parts.username and not parts.password:
        return url
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, "***:***@" + netloc, parts.path, parts.query, parts.fragment))
