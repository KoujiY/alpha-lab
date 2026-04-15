"""Reports 高階 API：組 id、寫檔、同步 index。"""

from __future__ import annotations

from datetime import date as date_type

from alpha_lab.reports.storage import (
    append_summary,
    load_index,
    read_report_markdown,
    upsert_in_index,
    write_report_markdown,
)
from alpha_lab.schemas.portfolio import RecommendResponse
from alpha_lab.schemas.report import (
    ReportCreate,
    ReportDetail,
    ReportMeta,
    ReportType,
)


def _build_report_id(
    report_type: ReportType,
    report_date: date_type,
    subject: str | None,
) -> str:
    d = report_date.isoformat()
    if report_type == "stock":
        if not subject:
            raise ValueError("stock report requires subject (symbol)")
        return f"stock-{subject}-{d}"
    if report_type == "research":
        if not subject:
            raise ValueError("research report requires subject (topic)")
        slug = subject.replace(" ", "-").replace("/", "-")
        return f"research-{slug}-{d}"
    if report_type == "portfolio":
        return f"portfolio-{d}"
    if report_type == "events":
        return f"events-{d}"
    raise ValueError(f"unknown report type: {report_type}")


def create_report(payload: ReportCreate) -> ReportMeta:
    """寫 markdown + 寫 summaries + 更新 index。若 id 重複會覆寫。"""

    report_date = payload.date or date_type.today()
    report_id = _build_report_id(payload.type, report_date, payload.subject)

    frontmatter: dict[str, object] = {
        "id": report_id,
        "type": payload.type,
        "title": payload.title,
        "symbols": payload.symbols,
        "tags": payload.tags,
        "date": report_date.isoformat(),
        "summary_line": payload.summary_line,
    }
    write_report_markdown(report_id, payload.body_markdown, frontmatter)

    rel_path = f"analysis/{report_id}.md"
    meta = ReportMeta(
        id=report_id,
        type=payload.type,
        title=payload.title,
        symbols=payload.symbols,
        tags=payload.tags,
        date=report_date,
        path=rel_path,
        summary_line=payload.summary_line,
        starred=False,
    )
    upsert_in_index(meta)

    if payload.summary_line:
        append_summary(report_date.isoformat(), payload.summary_line)

    return meta


def list_reports(
    type_filter: ReportType | None = None,
    tag_filter: str | None = None,
) -> list[ReportMeta]:
    items = load_index()
    if type_filter is not None:
        items = [m for m in items if m.type == type_filter]
    if tag_filter is not None:
        items = [m for m in items if tag_filter in m.tags]
    return items


def build_portfolio_report_markdown(resp: RecommendResponse) -> tuple[str, str]:
    """把 recommend API 回應組成 (summary_line, body_markdown)。

    body_markdown：依 style 分節、每節列出前幾檔 holding + 推薦理由。
    summary_line：簡述總檔數 + top style。
    """

    lines: list[str] = []
    lines.append(f"# 本次推薦組合（{resp.calc_date}）")
    lines.append("")
    lines.append(
        f"- generated_at: {resp.generated_at.isoformat()}"
    )
    lines.append(f"- calc_date: {resp.calc_date}")
    lines.append("")

    total_holdings = 0
    top_style: str | None = None
    for p in resp.portfolios:
        if p.is_top_pick:
            top_style = p.style
        total_holdings += len(p.holdings)

        lines.append(f"## {p.label}（{p.style}）")
        if p.is_top_pick:
            lines.append("")
            lines.append("⭐ **本次 Top Pick**")
        lines.append("")
        if not p.holdings:
            lines.append("_無符合條件的持股。_")
            lines.append("")
            continue

        lines.append("| 代號 | 名稱 | 權重 | 總分 |")
        lines.append("| --- | --- | ---: | ---: |")
        for h in p.holdings:
            total = h.score_breakdown.total_score
            total_str = f"{total:.1f}" if total is not None else "-"
            lines.append(
                f"| {h.symbol} | {h.name} | {h.weight * 100:.1f}% | {total_str} |"
            )
        lines.append("")

        for h in p.holdings:
            if not h.reasons:
                continue
            lines.append(f"### {h.symbol} {h.name}")
            for r in h.reasons:
                lines.append(f"- {r}")
            lines.append("")

    top_desc = top_style or (resp.portfolios[0].style if resp.portfolios else "n/a")
    summary_line = (
        f"calc_date={resp.calc_date}，{len(resp.portfolios)} 組風格、"
        f"合計 {total_holdings} 檔，Top Pick: {top_desc}"
    )

    body_markdown = "\n".join(lines).rstrip() + "\n"
    return summary_line, body_markdown


def create_portfolio_report(resp: RecommendResponse) -> ReportMeta:
    """將 recommend API 結果存成 portfolio 類型報告。日期取 calc_date。"""

    summary_line, body = build_portfolio_report_markdown(resp)
    report_date = date_type.fromisoformat(resp.calc_date)
    all_symbols = sorted(
        {h.symbol for p in resp.portfolios for h in p.holdings}
    )
    payload = ReportCreate(
        type="portfolio",
        title=f"本次推薦組合 {resp.calc_date}",
        body_markdown=body,
        summary_line=summary_line,
        symbols=all_symbols,
        tags=["portfolio", "recommend"],
        date=report_date,
    )
    return create_report(payload)


def get_report(report_id: str) -> ReportDetail | None:
    items = load_index()
    meta = next((m for m in items if m.id == report_id), None)
    if meta is None:
        return None
    fm_body = read_report_markdown(report_id)
    if fm_body is None:
        return None
    _, body = fm_body
    return ReportDetail(**meta.model_dump(), body_markdown=body)
