"""Jobs API routes。

POST /api/jobs/collect → 建立 job，排程背景執行
GET  /api/jobs/status/{id} → 查詢 job 狀態
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.schemas.job import JobCreateRequest, JobResponse
from alpha_lab.storage.engine import get_session_factory, session_scope
from alpha_lab.storage.models import Job

router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs/collect",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_collect_job(
    payload: JobCreateRequest, background_tasks: BackgroundTasks
) -> JobResponse:
    with session_scope() as session:
        job = create_job(session, job_type=payload.type, params=payload.params)
        session.flush()
        response = JobResponse.model_validate(job)

    background_tasks.add_task(
        run_job_sync,
        job_id=response.id,
        session_factory=get_session_factory(),
    )
    return response


@router.get("/jobs/status/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: int) -> JobResponse:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"job {job_id} not found")
        return JobResponse.model_validate(job)
