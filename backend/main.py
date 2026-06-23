"""
Manzil — FastAPI backend entrypoint.

Serves the Next.js frontend and exposes the core travel-planner API
by wrapping the existing manzil Python package.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the project root to sys.path so `backend` and `manzil` packages are
# importable regardless of how uvicorn spawns the process (direct vs reloader).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import feedback, health, images, plan, replan

# Load environment variables from project root .env file
load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(
    title="Manzil API",
    description="Multi-agent travel planner for northern Pakistan",
    version="1.0.0",
)

# CORS — allow Next.js dev server and production domain
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(plan.router, prefix="/api/v1")
app.include_router(replan.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(images.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"name": "Manzil API", "version": "1.0.0", "docs": "/docs"}
