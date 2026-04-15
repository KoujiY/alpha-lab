"""/api/reports 路由（Phase 4）。"""

from fastapi import APIRouter, HTTPException, Query

from alpha_lab.reports.service import create_report, get_report, list_reports
from alpha_lab.schemas.report import (
    ReportCreate,
    ReportDetail,
    ReportMeta,
    ReportType,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportMeta])
async def list_reports_endpoint(
    report_type: ReportType | None = Query(  # noqa: B008
        None, alias="type", description="報告類型過濾"
    ),
    tag: str | None = Query(None, description="tag 過濾（完全比對）"),
) -> list[ReportMeta]:
    return list_reports(type_filter=report_type, tag_filter=tag)


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report_endpoint(report_id: str) -> ReportDetail:
    detail = get_report(report_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")
    return detail


@router.post("", response_model=ReportMeta, status_code=201)
async def create_report_endpoint(payload: ReportCreate) -> ReportMeta:
    try:
        return create_report(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
