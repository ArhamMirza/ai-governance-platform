# Backend

The FastAPI API for the [AI Governance Platform](../README.md). Layered
`routers → services → repositories → models`, with `core/` for pure shared logic; see
[DESIGN.md](../DESIGN.md#4-backend) for the architecture and the rules the code follows.

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000, API docs at /docs in development
python -m app.seed              # optional: fictional demo data
```

Python 3.11 or newer.

## Settings

Read from `.env` (see `.env.example`):

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | SQLite by default (`sqlite:///./ai_governance.db`). |
| `EVIDENCE_STORAGE_DIR` | Where uploaded files are kept (UUID-named). |
| `SECRET_KEY` | Derives the key that encrypts stored AI provider keys and two-step secrets, and signs two-step sign-in tickets. Rotating it makes the stored secrets unreadable (sessions are unaffected). |
| `CORS_ORIGINS` | Exact origins to trust, comma separated. A wildcard is refused. |
| `ENVIRONMENT` | `development` (default), or `production` / `staging` for a real deployment. |
| `COOKIE_SECURE` | Must be `true` on a real deployment (the app refuses to start otherwise). |
| `SETUP_CODE` | Optional. The first account on a real deployment needs a setup code; unset, the server prints one at startup. |

With `ENVIRONMENT=production` the app also refuses the example `SECRET_KEY`, switches off the
API docs, and refuses to load demo data unless told `--allow-production`. See
[../deploy/README.md](../deploy/README.md).

## Database changes

Every schema change is an Alembic migration, and each is run **up, down and up again**
before it ships. Models and migrations must agree:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
alembic check            # "No new upgrade operations detected."
```

## Backups

```bash
python -m app.backup create --to ./backups --keep 14   # database + uploads, verified
python -m app.backup verify ./backups/ai-governance-backup-<stamp>.tar.gz
python -m app.backup restore ./backups/ai-governance-backup-<stamp>.tar.gz --to ../restore-test
```

See [deploy/README.md](../deploy/README.md#backups) for scheduling, what a backup does not
cover, and how to test a restore.

## What the AI costs

*Settings → Where the AI tokens go* (admins) shows tokens by kind of call. To see what the
assistant would send, without spending anything:

```bash
python -m app.prompt_report                      # a few sample questions
python -m app.prompt_report --questions q.txt    # your own, one per line
python -m app.prompt_report --json > before.json # save a run, change something, compare
```

## Tests and checks

```bash
pytest                       # about 2,000 tests: unit (pure functions, services) and integration (TestClient)
pytest --cov=app
ruff check .                 # lint
pip-audit --skip-editable    # known-vulnerable dependencies
```

Each test gets a fresh in-memory database. Sign-in flows are tested through the real
cookie flow rather than by overriding the session dependency, because the override would
bypass exactly what is being tested. Code that depends on time takes a clock.

## Useful commands

```bash
python -m app.cli.index_documents    # index whatever is waiting in the search queue
python -m app.seed --allow-production   # only if you really mean it on a production setup
```

## Where things are

`app/core` pure logic (risk scoring, schedules, TOTP, password rules, DLP rule validation,
prompts, chunking) · `app/services` business rules and approvals · `app/routers` HTTP ·
`app/repositories` queries · `app/models` tables · `app/schemas` request/response shapes ·
`alembic/versions` migrations. New code follows the layers: a router never touches the ORM,
and a service never imports FastAPI.
