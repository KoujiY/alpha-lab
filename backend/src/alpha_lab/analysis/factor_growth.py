"""Growth 因子：營收 YoY + EPS YoY，高者為佳。

Snapshot 格式：
    {symbol: {"revenue_yoy": float | None, "eps_yoy": float | None}}
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank


def compute_growth_scores(
    snapshot: dict[str, dict[str, float | None]],
) -> dict[str, float | None]:
    rev = {s: v.get("revenue_yoy") for s, v in snapshot.items()}
    eps = {s: v.get("eps_yoy") for s, v in snapshot.items()}

    rev_scores = percentile_rank(rev)
    eps_scores = percentile_rank(eps)

    result: dict[str, float | None] = {}
    for sym in snapshot:
        parts = [s for s in (rev_scores[sym], eps_scores[sym]) if s is not None]
        result[sym] = sum(parts) / len(parts) if parts else None
    return result
