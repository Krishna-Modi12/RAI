"""FastAPI backend service entry point for Renewable Asset Intelligence."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from rai.agent.interfaces import probe_capabilities
from services.api.errors import APIError, api_error_handler, generic_http_error_handler
from services.api.routers import assets, evaluation, fleet, health, knowledge, simulator, soiling

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("rai.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cap = probe_capabilities()
    log.info("Starting Renewable Asset Intelligence API Service...")
    log.info(
        "Capabilities status: evidence=%s, cases=%s, economics=%s, knowledge=%s, needle=%s",
        cap.evidence,
        cap.cases,
        cap.economics,
        cap.knowledge,
        cap.needle,
    )
    yield
    log.info("Shutting down Renewable Asset Intelligence API Service.")


app = FastAPI(
    title="Renewable Asset Intelligence API",
    description="Operational predictive maintenance & environmental risk intelligence API.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for Next.js frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers complying with API Contract {"detail": "...", "code": "..."}
app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, generic_http_error_handler)  # type: ignore[arg-type]

# Include domain routers
app.include_router(health.router)
app.include_router(fleet.router)
app.include_router(assets.router)
app.include_router(soiling.router)
app.include_router(knowledge.router)
app.include_router(simulator.router)
app.include_router(evaluation.router)


@app.get("/")
def root():
    return {
        "service": "Renewable Asset Intelligence API",
        "docs": "/docs",
        "health": "/api/health",
        "version": "0.1.0",
    }
