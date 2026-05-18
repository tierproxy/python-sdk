"""Cost guardrails used by TierProxy when monthly_budget_usd is configured.
Keeps the heavy logic out of client.py."""

from __future__ import annotations

from tierproxy.errors import TierProxyError


class BudgetExceededError(TierProxyError):
    """Raised when an inbound request would push monthly cost over the configured budget."""


def check_budget(
    estimated_cost_usd: float,
    spent_usd: float,
    monthly_budget_usd: float,
) -> None:
    if spent_usd + estimated_cost_usd > monthly_budget_usd:
        raise BudgetExceededError(
            f"Refusing request: estimated cost ${estimated_cost_usd:.4f} would push "
            f"month-to-date spend (${spent_usd:.2f}) over monthly_budget_usd "
            f"(${monthly_budget_usd:.2f})",
        )
