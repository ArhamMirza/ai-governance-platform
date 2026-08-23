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

## Demo Data

```bash
cd backend
python -m app.seed
```

Populates a few policies, procedures, AI systems, and risk assessments
through the real service layer (so audit history, computed risk scores,
etc. all come out correctly). Safe to run more than once — it skips if
the database already has policies in it.

## Testing

```bash
# backend
cd backend && pytest --cov=app

# frontend
cd frontend && npm test
```

## Git Workflow

- `main` is protected and always kept working — changes land via Pull Request,
  not direct pushes.
- One feature branch per vertical slice: `feat/<short-name>` (or `fix/`, `chore/`,
  `docs/`, `test/` for their respective purposes). Push the branch and open a PR
  rather than merging locally.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat: add policy approval workflow`, `test: cover risk score edge cases`, etc.
- Keep commits small and logically scoped — one concern per commit.
- Work is tracked as GitHub Issues; PRs reference the issue they close
  (`Closes #12`).

## CI/CD

- **CI** (`.github/workflows/ci.yml`): every PR and push to `main` runs backend
  lint (`ruff`) + tests (`pytest`) and frontend lint (`oxlint`) + tests
  (`vitest`) + production build. Branch protection requires these checks to
  pass before a PR can merge.
- **Releases** (`.github/workflows/release.yml`): pushing a tag matching
  `v*.*.*` (e.g. `v0.1.0`) auto-creates a GitHub Release with notes generated
  from the commit history since the last tag.
  ```bash
  git tag v0.1.0
  git push origin v0.1.0
  ```
  There's no separate deployment step — this is a locally-run app, so a
  "release" just marks a known-good, tagged snapshot of the code. A
  Docker-based distribution path is a planned post-MVP extension
  (see DESIGN.md §9).
