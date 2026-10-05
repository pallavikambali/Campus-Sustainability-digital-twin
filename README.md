# Campus Sustainability Digital Twin

Phase 1 establishes the project foundation, PostgreSQL schema, and minimal API and frontend shells. It does not include simulation, anomaly detection, dashboard features, Computer Vision, GenAI, recommendations, or reporting.

## Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm
- Docker Compose

## Configure and initialize

Run these commands from the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d db
Set-Location backend
uv sync --dev
uv run alembic upgrade head
uv run pytest
uv run ruff check .
```

The migration creates the six Phase 1 tables and seeds Academic Block, Library, and Hostel Block. The local database is PostgreSQL 16 and is compatible with the intended Supabase PostgreSQL deployment.

## Run the applications

In one terminal, from the repository root:

```powershell
Set-Location backend
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal, from the repository root:

```powershell
Set-Location frontend
npm install
npm run dev
```

The frontend is available at <http://localhost:5173>. The API health endpoint at <http://localhost:8000/api/v1/health> checks PostgreSQL connectivity.

## Frontend checks

From `frontend`:

```powershell
npm run build
```

The build runs the TypeScript checker before bundling with Vite.

## Database operations

From `backend`:

```powershell
uv run alembic upgrade head
uv run alembic current
```

Stop the local database with `docker compose down`. Its data remains in the named Docker volume. Removing that volume is destructive and is not required for normal development.
