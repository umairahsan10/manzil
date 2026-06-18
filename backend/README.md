# Manzil Backend

Self-contained FastAPI service for the Manzil travel planner. It includes its own copy of the core `manzil` Python package and the `data/` knowledge base so it can be deployed independently.

> **Independence note:** This backend does not depend on the `manzil/` folder at the project root. That folder is kept only for the legacy Streamlit UI, tests, scripts, and evals. You can delete it without breaking the FastAPI service.

## Local Development

1. Create a virtual environment (Python 3.12 recommended):
   ```bash
   python3.12 -m venv ../.venv
   ../.venv/Scripts/python -m pip install -r requirements.txt
   ```

2. Copy the project root `.env.example` to `.env` and configure:
   ```bash
   cp ../.env.example ../.env
   ```

3. Start the server from the project root:
   ```bash
   ../.venv/Scripts/python -m uvicorn backend.main:app --reload --port 8000
   ```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET`  | `/api/v1/health` | System health and config |
| `POST` | `/api/v1/plan` | Generate candidates + debate |
| `POST` | `/api/v1/plan/stream` | SSE streaming debate |
| `POST` | `/api/v1/replan` | Replan with disruption |
| `POST` | `/api/v1/feedback` | Submit feedback |
| `GET`  | `/api/v1/feedback/stats` | Feedback statistics |

## Architecture

- `manzil/` — Core Python package (agents, recommender, schemas, tools)
- `data/` — Knowledge base JSON files and local corpus
- `routers/` — FastAPI route handlers
- `repositories/` — Data access abstraction (JSON for Phase 1, Postgres for Phase 2)
- `schemas.py` — API request/response Pydantic models
- `dependencies.py` — Injectable dependencies

The backend is self-contained: `backend/main.py` adds `backend/` to `sys.path` so the local `manzil` package is imported. It no longer depends on the `manzil/` folder at the project root.
