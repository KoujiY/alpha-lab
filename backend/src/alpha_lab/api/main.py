from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alpha_lab.api.routes import education, glossary, health, jobs, portfolios, stocks
from alpha_lab.storage.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_database()
    yield


app = FastAPI(
    title="alpha-lab",
    description="台股長線投資個人工具 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: 允許前端 dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(glossary.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(portfolios.router, prefix="/api")
app.include_router(education.router, prefix="/api")
