"""Quality 因子：ROE + 毛利率（高者佳）+ 負債比（低者佳）+ FCF（高者佳）。

Snapshot 格式：
    {symbol: {"roe": f | None, "gross_margin": f | None,
              "debt_ratio": f | None, "fcf": f | None}}

FCF 於 Phase 3 Task F3 以 OCF（近四季加總）為代理；未扣 CapEx。
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank, percentile_rank_inverted


def compute_quality_scores(
    snapshot: dict[str, dict[str, float | None]],
) -> dict[str, float | None]:
    roe = percentile_rank({s: v.get("roe") for s, v in snapshot.items()})
    gm = percentile_rank({s: v.get("gross_margin") for s, v in snapshot.items()})
    dr = percentile_rank_inverted(
        {s: v.get("debt_ratio") for s, v in snapshot.items()}
    )
    fcf = percentile_rank({s: v.get("fcf") for s, v in snapshot.items()})

    result: dict[str, float | None] = {}
    for sym in snapshot:
        parts = [
            s for s in (roe[sym], gm[sym], dr[sym], fcf[sym]) if s is not None
        ]
        result[sym] = sum(parts) / len(parts) if parts else None
    return result
