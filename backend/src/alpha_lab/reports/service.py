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
