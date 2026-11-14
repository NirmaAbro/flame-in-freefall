"""IGNIS backend. Every route is registered here once (task T0).

After T0 a task changes its own router file, not this file.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import (
    ai,
    compare,
    coverage,
    dashboard,
    export,
    filters,
    habitats,
    investigations,
    rank,
    tests,
    variables,
)
from .schemas import Health

API_PREFIX = "/api/v1"

app = FastAPI(title="IGNIS backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{API_PREFIX}/health", response_model=Health)
def health():
    return {"status": "ok"}


for module in (
    investigations,
    filters,
    dashboard,
    compare,
    coverage,
    variables,
    ai,
    tests,
    habitats,
    export,
    rank,
):
    app.include_router(module.router, prefix=API_PREFIX)
