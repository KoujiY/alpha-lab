from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alpha_lab.api.routes import health

app = FastAPI(
    title="alpha-lab",
    description="台股長線投資個人工具 API",
    version="0.1.0",
)

# CORS: 允許前端 dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
