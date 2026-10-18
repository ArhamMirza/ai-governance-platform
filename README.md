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

## Governing staff use of AI tools

The platform can also govern what employees do with AI, not only document it:

- **Register of AI tools** — which third-party tools are approved, with what
  data they may be given. Employees ask for a tool from their staff login; the
  Chief AI Governance Officer decides.
- **Data rules (DLP)** — what must not be pasted or typed into AI tools. The
  rules are evaluated in the employee's browser; the text never reaches the server.
- **Browser extension** (`extension/`, Chrome and Edge) — carries it out:
  warns on or blocks unapproved AI sites, checks text before it is sent, and
  reports daily counts (never the text). See
  [extension/README.md](extension/README.md) for what it can and can't do and
  how to roll it out.

## Accounts and sign-in

- **Passwords** need at least 12 characters and are refused if they are a common
  word (even dressed up, like `P@ssw0rd2024!`), a keyboard or number run, almost
  all one character, or built from the person's own name or email. The last five
  passwords can't be reused.
- **Temporary passwords.** An account an administrator creates, or whose password
  they reset, can do nothing but choose a new password at first sign-in. Existing
  accounts whose password falls short of the rules are asked to change it the same way.
- **Resetting.** *Users → Reset password* issues a one-time password, shown once and
  never stored readably, and signs the person out everywhere.
- **Sessions** end everywhere when a password is changed or reset, a role is changed,
  or an account is deactivated. *Your account* has "Sign out of other devices".
- **Lockout.** Five wrong passwords lock an account for 15 minutes; 20 wrong attempts
  from one address block that address. Behind a reverse proxy, forward the real client
  address (`uvicorn --proxy-headers`) or every user will appear to share one.
- **Audit trail.** Sign-ins, failed sign-ins, lockouts, sign-outs, password changes and
  resets are recorded against the account (with the address), in the audit log.

### Hardening for a real deployment

With `ENVIRONMENT=production` (or `staging`) the platform is stricter, and
[deploy/](deploy/README.md) has the proxy configuration to go with it:

- **First account needs a setup code**, printed in the server's log at startup (or set
  as `SETUP_CODE`), so whoever reaches a new server first can't claim it.
- **Every response carries protective headers**: `nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Permissions-Policy`, a policy that makes downloaded files inert,
  `Cache-Control: no-store`, and HSTS when cookies are secure.
- **The session cookie** is `HttpOnly`, `SameSite=Strict`, and (over https) carries the
  browser-enforced `__Host-` prefix.
- **Cross-site requests are refused**: a state-changing request carrying the session
  cookie from another website's origin gets a 403, on top of SameSite and CORS.
- **CORS** allows only the listed origins (a wildcard is refused at startup), and only
  the methods and headers the app uses.
- **The API docs are switched off**, and the demo-data loader refuses to run unless
  told `--allow-production`.
- The built frontend works under a strict Content-Security-Policy (no inline scripts);
  CI checks the built page.

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
  lint (`ruff`) + tests (`pytest`), frontend lint (`oxlint`) + tests
  (`vitest`) + production build, and the same for the browser extension. Branch protection requires these checks to
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

## License

Apache License 2.0 — see [LICENSE](LICENSE).
