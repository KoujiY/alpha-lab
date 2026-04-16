"""/api/reports 路由（Phase 4）。"""

from fastapi import APIRouter, HTTPException, Query

from alpha_lab.reports.service import (
    create_report,
    delete_report,
    get_report,
    list_reports,
    update_report,
)
from alpha_lab.schemas.report import (
    ReportCreate,
    ReportDetail,
    ReportMeta,
    ReportType,
    ReportUpdate,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportMeta])
async def list_reports_endpoint(
    report_type: ReportType | None = Query(  # noqa: B008
        None, alias="type", description="報告類型過濾"
    ),
    tag: str | None = Query(None, description="tag 過濾（完全比對）"),
    symbol: str | None = Query(None, description="以 symbol 過濾（完全比對）"),
    q: str | None = Query(None, description="全文搜尋：title/summary/tags/symbols"),
) -> list[ReportMeta]:
    return list_reports(
        type_filter=report_type, tag_filter=tag, symbol=symbol, query=q
    )


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


@router.patch("/{report_id}", response_model=ReportMeta)
async def patch_report_endpoint(
    report_id: str, payload: ReportUpdate
) -> ReportMeta:
    updated = update_report(report_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="report not found")
    return updated


@router.delete("/{report_id}", status_code=204)
async def delete_report_endpoint(report_id: str) -> None:
    if not delete_report(report_id):
        raise HTTPException(status_code=404, detail="report not found")
