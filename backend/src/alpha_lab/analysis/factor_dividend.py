"""Dividend 因子：當期殖利率，高者為佳。

Snapshot 格式：{symbol: yield | None}
yield 以小數表示（0.05 = 5%）。
連續配息年數、穩定度留後續 Phase。
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank


def compute_dividend_scores(
    snapshot: dict[str, float | None],
) -> dict[str, float | None]:
    return percentile_rank(snapshot)
