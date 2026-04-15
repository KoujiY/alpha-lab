"""Value 因子：PE + PB，低者為佳。

Snapshot 格式：
    {symbol: {"pe": float | None, "pb": float | None}}

回傳：
    {symbol: value_score (0-100) | None}

規則：PE 與 PB 各自做 percentile_rank_inverted（低者得高分），
      取可用因子的平均；若兩者皆 None → None。
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank_inverted


def compute_value_scores(
    snapshot: dict[str, dict[str, float | None]],
) -> dict[str, float | None]:
    pe_values = {s: v.get("pe") for s, v in snapshot.items()}
    pb_values = {s: v.get("pb") for s, v in snapshot.items()}

    pe_scores = percentile_rank_inverted(pe_values)
    pb_scores = percentile_rank_inverted(pb_values)

    result: dict[str, float | None] = {}
    for sym in snapshot:
        parts = [s for s in (pe_scores[sym], pb_scores[sym]) if s is not None]
        result[sym] = sum(parts) / len(parts) if parts else None
    return result
