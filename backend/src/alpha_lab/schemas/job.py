"""Job API Pydantic schemas。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from alpha_lab.jobs.types import JobType


class JobCreateRequest(BaseModel):
    type: JobType
    params: dict[str, Any] = {}


class JobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    result_summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}
