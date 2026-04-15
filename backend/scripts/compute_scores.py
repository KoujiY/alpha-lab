"""手動觸發評分 pipeline。

用法：
    python scripts/compute_scores.py [--date YYYY-MM-DD]

不帶 --date → 今天。
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime

from alpha_lab.analysis.pipeline import score_all
from alpha_lab.storage.engine import session_scope


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute factor scores")
    parser.add_argument("--date", type=str, default=None, help="YYYY-MM-DD")
    args = parser.parse_args()

    calc_date = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(UTC).date()
    )
    with session_scope() as session:
        n = score_all(session, calc_date)
    print(f"Scored {n} symbols for {calc_date.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
