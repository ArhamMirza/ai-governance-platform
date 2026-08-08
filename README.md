# AI Governance Platform

A locally-run application for managing AI governance — policies, procedures,
an AI system inventory, risk assessments, and supporting evidence — aligned to
frameworks such as the EU AI Act and ISO/IEC 42001.

See [DESIGN.md](DESIGN.md) for the full architecture and data model.

## Stack

- **Frontend**: React + TypeScript + Vite, TanStack Query, feature-based folders
- **Backend**: FastAPI (Python), SQLAlchemy + Alembic, layered
  routers → services → repositories
- **Database**: SQLite (file-based, local)

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs` once running.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

App available at `http://localhost:5173`.

## Testing

```bash
# backend
cd backend && pytest --cov=app

# frontend
cd frontend && npm test
```

## Git Workflow

- `main` is always kept working.
- One feature branch per vertical slice: `feat/<short-name>` (or `fix/`, `chore/`,
  `docs/`, `test/` for their respective purposes), merged back with `--no-ff`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat: add policy approval workflow`, `test: cover risk score edge cases`, etc.
- Keep commits small and logically scoped — one concern per commit.
