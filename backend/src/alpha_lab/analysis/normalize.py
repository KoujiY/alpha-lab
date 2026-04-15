"""橫截面百分位歸一化工具。

同一 calc_date 所有 symbol 一起排名，轉成 0-100 分。
- percentile_rank: 值越大分數越高（適用 ROE、營收 YoY）
- percentile_rank_inverted: 值越小分數越高（適用 PE、PB、負債比）

None 會被保留為 None（不參與排名）。
"""

from __future__ import annotations


def _rank_core(values: dict[str, float | None]) -> dict[str, float | None]:
    items = [(k, v) for k, v in values.items() if v is not None]
    result: dict[str, float | None] = dict.fromkeys(values)
    if not items:
        return result
    if len(items) == 1:
        result[items[0][0]] = 50.0
        return result

    sorted_items = sorted(items, key=lambda kv: kv[1])
    n = len(sorted_items)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_items[j + 1][1] == sorted_items[i][1]:
            j += 1
        avg_rank = (i + j) / 2
        pct = (avg_rank / (n - 1)) * 100.0
        for k in range(i, j + 1):
            result[sorted_items[k][0]] = pct
        i = j + 1

    return result


def percentile_rank(values: dict[str, float | None]) -> dict[str, float | None]:
    """值越大分數越高。"""
    return _rank_core(values)


def percentile_rank_inverted(
    values: dict[str, float | None],
) -> dict[str, float | None]:
    """值越小分數越高（用於 PE、PB、負債比等）。"""
    ranked = _rank_core(values)
    return {k: (100.0 - v if v is not None else None) for k, v in ranked.items()}
