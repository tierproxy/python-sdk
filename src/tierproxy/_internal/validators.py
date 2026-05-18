from __future__ import annotations

import re

_API_KEY_RE = re.compile(r"^[A-Za-z0-9_.\-]{16,128}$")


def validate_api_key(key: str) -> None:
    if not _API_KEY_RE.match(key):
        raise ValueError(
            "api_key must match [A-Za-z0-9_.-]{16,128}; "
            "received an invalid value (length / chars). "
            "Regenerate the key in the dashboard."
        )


def validate_base_url(base_url: str, allow_insecure: bool) -> None:
    if not base_url.startswith("https://") and not allow_insecure:
        raise ValueError(
            f"TierProxy refuses insecure base_url={base_url!r}; use https:// "
            "or pass allow_insecure=True for a local gateway."
        )
