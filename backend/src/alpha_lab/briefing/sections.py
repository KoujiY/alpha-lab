"""Daily briefing section builders。

每個 builder 接收結構化資料（dict list），回傳 Markdown 字串。
不直接操作 DB——由上層 daily.py 查詢後傳入。
"""

from __future__ import annotations

from datetime import date
from typing import Any


def build_market_overview_section(
    prices: list[dict[str, Any]],
    trade_date: date,
) -> str:
    lines = [f"## 市場概況（{trade_date.isoformat()}）", ""]
    if not prices:
        lines.append("_無資料_")
        return "\n".join(lines) + "\n"

    lines.append("| 代號 | 名稱 | 收盤 | 漲跌 | 漲跌% | 成交量 |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for p in prices:
        change = p.get("change", 0)
        sign = "+" if change > 0 else ""
        pct = p.get("change_pct", 0)
        pct_sign = "+" if pct > 0 else ""
        lines.append(
            f"| {p['symbol']} | {p['name']} "
            f"| {p['close']:.2f} "
            f"| {sign}{change:.2f} "
            f"| {pct_sign}{pct:.2f}% "
            f"| {p['volume']:,} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_institutional_section(
    inst: list[dict[str, Any]],
    trade_date: date,
) -> str:
    lines = [f"## 法人動向（{trade_date.isoformat()}）", ""]
    if not inst:
        lines.append("_無資料_")
        return "\n".join(lines) + "\n"

    lines.append("| 代號 | 名稱 | 外資 | 投信 | 自營商 | 合計 |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for row in inst:
        lines.append(
            f"| {row['symbol']} | {row['name']} "
            f"| {row['foreign_net']:,} "
            f"| {row['trust_net']:,} "
            f"| {row['dealer_net']:,} "
            f"| {row['total_net']:,} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_events_section(events: list[dict[str, Any]]) -> str:
    lines = ["## 重大訊息", ""]
    if not events:
        lines.append("_無資料_")
        return "\n".join(lines) + "\n"

    for ev in events:
        lines.append(
            f"- **{ev['symbol']}** {ev['title']}"
            f"（{ev['event_type']}，{ev['event_datetime']}）"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_portfolio_tracking_section(portfolios: list[dict[str, Any]]) -> str:
    lines = ["## 組合追蹤", ""]
    if not portfolios:
        lines.append("_無儲存的組合_")
        return "\n".join(lines) + "\n"

    lines.append("| # | 名稱 | NAV | 報酬% | 基準日 |")
    lines.append("| ---: | --- | ---: | ---: | --- |")
    for p in portfolios:
        lines.append(
            f"| {p['id']} | {p['label']} "
            f"| {p['nav']:.4f} "
            f"| {p['return_pct']:+.2f}% "
            f"| {p['base_date']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"
