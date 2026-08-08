# AI Governance Platform — MVP Design Document

## 1. Purpose & Scope

A locally-run, full-stack application to help an organization manage AI governance
activities in line with the **EU AI Act** and **ISO/IEC 42001** (AI Management
System standard). The MVP focuses on three pillars:

1. **Policy Management** — author, version, approve, and publish governance policies.
   Policies are **organization-wide**: they do not reference any specific AI System.
2. **Procedure Management** — operational procedures/controls that implement policies.
   Also **organization-wide**, with no link to specific AI Systems; a Procedure may
   optionally link to the Policy it implements.
3. **AI System Inventory** — the register of every AI system/use-case in the
   organization (potentially many entries), each with a lifecycle stage and risk tier.
4. **AI Risk Assessment** — performed **against a specific AI System** from the
   inventory (one assessment always belongs to exactly one system); classify risk,
   track mitigations and residual risk.
5. **Evidence Management** — attach supporting documents/files to policies,
   procedures, risk assessments, and risk items as proof of compliance activity.

In short: Policies and Procedures live above the AI System Inventory (they govern
the organization as a whole); Risk Assessments live below it (each one is scoped
to one entry in the inventory).

Everything else (auditing trails, dashboards, compliance mapping) supports these
pillars. The system runs entirely locally: React frontend, FastAPI backend,
SQLite database, local filesystem storage — no external services required for the MVP.

### Out of scope for MVP (explicitly deferred)
- Multi-tenant / multi-org support
- Authentication providers (SSO/OAuth) — MVP uses simple local auth (single admin
  user or basic username/password) since it runs locally
- Automated evidence collection from external systems (model registries, MLOps
  pipelines)
- PDF/CE-marking style regulatory submission generation
- Real-time collaboration (concurrent editing)
- Notifications/email
- Full Annex III/IV documentation generators (technical documentation, conformity
  assessment) — the MVP produces the underlying data model these could be built on
  later

## 2. Why This Shape (Research Summary)

**Backend — FastAPI.** Best-practice 2026 guidance converges on a layered structure
that separates **routers → services → repositories → models/schemas**, with
cross-cutting concerns (config, security, db session) in a `core/` module. For a
single-domain MVP a layered structure is preferred over full domain-driven design;
the code should be *organized so it can migrate to a domain-per-folder layout* once
more modules (e.g. vendor risk, incident management) are added later. Dependency
injection (FastAPI's `Depends`) is used to keep services testable in isolation from
HTTP and from the database.

**Frontend — React.** 2026 guidance favors **feature-based / vertical-slice**
folders (group by domain: `policies/`, `procedures/`, `risk-assessments/`) over
grouping by technical type (`components/`, `hooks/`). Business/domain logic is kept
out of components via custom hooks and a thin API-client layer, so UI framework
choice stays a swappable detail. Server state (data fetched from the API) is
managed via **TanStack Query**; local/UI state via component state or a small store
if needed — no heavy global state library required for MVP.

**Compliance framework mapping.**
- *ISO/IEC 42001* is structured as a PDCA (Plan-Do-Check-Act) management system,
  clauses 4–10, with **Clause 6.1 (risk & opportunity planning)** and **Clause 8.4
  (AI system impact assessment)** as the core risk-assessment obligations, backed by
  Annex A controls and required "documented information" (i.e., policies and
  procedures with version/approval history).
- *EU AI Act* (as amended, Digital Omnibus timeline) requires for
  high-risk systems: a documented **risk management system**, **technical
  documentation**, **logging**, **human oversight** measures, and a **quality
  management system**. Deadlines for Annex III/Annex I systems have shifted to
  Dec 2027 / Aug 2028 respectively, but organizations are building the underlying
  governance infrastructure now.

  The data model below is designed so that a "Risk Assessment" record can carry
  **framework tags** (e.g. `ISO42001:8.4`, `EU_AI_ACT:Art.9`) — a lightweight
  mapping table rather than hardcoded regulatory logic, so new frameworks (NIST AI
  RMF, etc.) can be added without schema changes.

  Both frameworks also expect **documented information / evidence** as proof that
  a control, policy, or assessment was actually carried out (ISO 42001 Clause 7.5;
  EU AI Act technical documentation and logging obligations). The MVP treats
  evidence as a first-class entity rather than a bolt-on so this is covered from
  day one, using local filesystem storage (no cloud dependency needed to run
  locally).

## 3. High-Level Architecture

```
┌──────────────────────────────┐        ┌───────────────────────────────────┐
│           Frontend            │  HTTP  │              Backend               │
│  React + TypeScript + Vite    │ <────> │  FastAPI (Python)                  │
│  TanStack Query (server state)│  JSON  │  routers → services → repositories │
│  Feature-based folders        │        │  Pydantic schemas / SQLAlchemy ORM │
└──────────────────────────────┘        └───────────────┬─────────────────────┘
                                                          │
                                                   ┌──────▼──────┐
                                                   │   SQLite     │
                                                   │  (file-based)│
                                                   └──────────────┘
```

Both processes run locally (`uvicorn` on e.g. :8000, Vite dev server on :5173),
communicating over HTTP with CORS enabled for local dev. No Docker required for
MVP, though a `docker-compose.yml` can be added later without changing the
architecture.

## 4. Backend Design (FastAPI)

### 4.1 Directory structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory, router registration, CORS
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings), env vars
│   │   ├── database.py         # SQLAlchemy engine/session, Base
│   │   └── security.py         # Password hashing, simple auth (MVP)
│   ├── models/                 # SQLAlchemy ORM models (one file per aggregate)
│   │   ├── user.py
│   │   ├── policy.py
│   │   ├── procedure.py
│   │   ├── ai_system.py
│   │   ├── risk_assessment.py
│   │   ├── evidence.py
│   │   └── audit_log.py
│   ├── schemas/                # Pydantic request/response models (mirrors models/)
│   │   ├── policy.py
│   │   ├── procedure.py
│   │   ├── ai_system.py
│   │   ├── risk_assessment.py
│   │   └── evidence.py
│   ├── repositories/           # DB access only, no business rules
│   │   ├── policy_repository.py
│   │   ├── procedure_repository.py
│   │   ├── ai_system_repository.py
│   │   ├── risk_assessment_repository.py
│   │   └── evidence_repository.py
│   ├── services/                # Business logic, orchestration, validation rules
│   │   ├── policy_service.py
│   │   ├── procedure_service.py
│   │   ├── ai_system_service.py
│   │   ├── risk_assessment_service.py
│   │   ├── evidence_service.py   # validates file type/size, writes to storage, links entity
│   │   └── audit_service.py
│   ├── routers/                 # HTTP layer only: parse request, call service, return
│   │   ├── policies.py
│   │   ├── procedures.py
│   │   ├── ai_systems.py
│   │   ├── risk_assessments.py
│   │   └── evidence.py
│   ├── dependencies.py          # shared Depends() providers (db session, current_user)
│   └── seed.py                  # optional demo data seeding script
├── tests/
│   ├── conftest.py              # test DB fixture (in-memory SQLite), TestClient fixture
│   ├── unit/                     # service-layer tests with repositories mocked
│   │   ├── test_policy_service.py
│   │   ├── test_risk_assessment_service.py
│   │   └── ...
│   └── integration/               # router-level tests hitting a real (test) DB
│       ├── test_policies_api.py
│       └── ...
├── alembic/                       # DB migrations (recommended even for SQLite MVP)
│   └── versions/
├── storage/
│   └── evidence/                  # uploaded files, one subfolder per entity or UUID-named
├── alembic.ini
├── pyproject.toml                 # deps + ruff/black/mypy config
└── .env.example
```

`storage/` is gitignored; its path is configurable via `EVIDENCE_STORAGE_DIR` in
`.env` so it can later be swapped for a mounted volume or object store without
touching `evidence_service.py`'s interface.

**Rule of thumb enforced across the codebase:** routers never touch the ORM
directly; services never import FastAPI (`Request`/`HTTPException` stay in
routers, services raise plain domain exceptions that routers translate to HTTP
errors). This keeps services unit-testable without spinning up FastAPI, and keeps
repositories swappable (e.g. SQLite → Postgres later) without touching business
logic.

### 4.2 Core domain model

| Entity | Key fields | Notes |
|---|---|---|
| `User` | id, name, email, role (`admin`, `contributor`, `viewer`) | Minimal RBAC for MVP |
| `Policy` | id, title, description, status (`draft/in_review/approved/retired`), version, owner_id, content (markdown), effective_date | Organization-wide; **no** AI System reference. Versioned via `PolicyVersion` child table |
| `PolicyVersion` | id, policy_id, version_no, content, changed_by, changed_at, change_note | Full history, append-only |
| `Procedure` | id, title, description, status, policy_id (FK, optional link to a Policy), owner_id, content | Organization-wide; **no** AI System reference. Same versioning pattern as Policy |
| `AISystem` | id, name, description, purpose, owner_id, lifecycle_stage (`design/dev/testing/deployed/retired`), risk_tier (`unacceptable/high/limited/minimal`) | One row per entry in the **AI System Inventory** — the org can register any number of systems here |
| `RiskAssessment` | id, ai_system_id (FK, **required**), framework_tags (JSON list, e.g. `["ISO42001:8.4","EU_AI_ACT:Art.9"]`), status (`draft/in_progress/completed`), assessor_id, assessment_date, overall_risk_rating | Header record — always scoped to exactly **one** AI System from the inventory (a system can have many assessments over time, e.g. re-assessed each release) |
| `RiskItem` | id, risk_assessment_id, category, description, likelihood (1-5), impact (1-5), inherent_risk_score (computed), mitigation, residual_likelihood, residual_impact, residual_risk_score, control_owner_id, status | Line items within an assessment — supports the standard likelihood × impact matrix |
| `Evidence` | id, entity_type (`Policy`/`Procedure`/`RiskAssessment`/`RiskItem`), entity_id, filename, content_type, size_bytes, storage_path, description, uploaded_by, uploaded_at | Polymorphic attachment — one table serves all entity types rather than a join table per entity |
| `AuditLogEntry` | id, entity_type, entity_id, action, actor_id, timestamp, diff (JSON) | Append-only trail for every create/update/status-change across the above entities, including evidence uploads/deletes — supports ISO 42001 "documented information" / traceability expectations |
| `FrameworkControl` (reference/lookup table) | id, framework (`ISO42001`/`EU_AI_ACT`), clause_ref, title, description | Static seed data used to populate the framework_tags picker and show clause text inline — not user-editable in MVP |

Risk scoring: `inherent_risk_score = likelihood * impact` (1–25), same for residual.
Overall assessment rating rolls up from the max/average of its risk items — kept as
a simple, explicit business rule in `risk_assessment_service.py` so it's easy to
unit test and to swap for a more sophisticated model later.

### 4.3 API surface (MVP)

REST, versioned under `/api/v1`, JSON in/out, OpenAPI docs auto-generated at `/docs`.

```
GET/POST         /api/v1/policies
GET/PUT/DELETE   /api/v1/policies/{id}
POST             /api/v1/policies/{id}/submit-for-review
POST             /api/v1/policies/{id}/approve
GET              /api/v1/policies/{id}/versions

GET/POST         /api/v1/procedures
GET/PUT/DELETE   /api/v1/procedures/{id}
... (same review/approve/version pattern)

GET/POST         /api/v1/ai-systems
GET/PUT/DELETE   /api/v1/ai-systems/{id}

GET/POST         /api/v1/risk-assessments
GET/PUT/DELETE   /api/v1/risk-assessments/{id}
POST             /api/v1/risk-assessments/{id}/items
PUT/DELETE       /api/v1/risk-assessments/{id}/items/{item_id}

GET              /api/v1/framework-controls?framework=ISO42001
GET              /api/v1/audit-log?entity_type=Policy&entity_id=...
GET              /api/v1/dashboard/summary   # counts by status/risk tier for home page

POST             /api/v1/evidence?entity_type=RiskItem&entity_id={id}   # multipart file upload
GET              /api/v1/evidence?entity_type=RiskItem&entity_id={id}   # list attachments for an entity
GET              /api/v1/evidence/{id}/download
DELETE           /api/v1/evidence/{id}
```

Every mutating endpoint writes an `AuditLogEntry` via `audit_service` — this is
called from the service layer (not duplicated per-router) so it can never be
forgotten.

`evidence_service.py` enforces MVP guardrails centrally: an allow-list of file
extensions/content-types, a max file size (e.g. 25 MB, configurable), and a
UUID-based storage filename (the original filename is kept only as metadata) to
avoid path-traversal or collision issues. Deleting an `Evidence` row also deletes
the underlying file — handled in the service, not the router, so it's covered by
unit tests without needing a running server.

### 4.4 Testing strategy (backend)

- **Unit tests** (majority of coverage): test services with repositories replaced
  by fakes/mocks — pure business logic (status transitions, risk scoring, version
  bumping) with no DB or HTTP involved. Fast, run on every save.
- **Integration tests**: `TestClient` against routers, backed by a real SQLite
  DB created fresh per test session (file `:memory:` or temp file), verifying
  request/response contracts, status codes, and validation errors.
- **Fixtures** (`conftest.py`): DB session fixture with transaction rollback per
  test; factory fixtures (e.g. `make_policy()`) instead of hardcoded fixtures, to
  keep tests readable as the schema grows.
- Evidence tests use pytest's `tmp_path` fixture as the storage directory (via
  `EVIDENCE_STORAGE_DIR` override) so upload/delete tests touch a real filesystem
  without polluting the repo, and are cleaned up automatically per test.
- Target: every service function and every router path has at least one test;
  status-transition logic (draft→review→approved) and risk-scoring math get
  exhaustive edge-case tests since those encode the compliance-relevant rules.
- Tooling: `pytest`, `pytest-cov`, `httpx` (via TestClient), `ruff` + `mypy` in CI/
  pre-commit.

## 5. Frontend Design (React)

### 5.1 Directory structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── App.tsx                # router setup, layout shell
│   │   ├── routes.tsx
│   │   └── queryClient.ts         # TanStack Query client config
│   ├── shared/                     # truly cross-feature only
│   │   ├── api/httpClient.ts       # fetch wrapper, base URL, error handling
│   │   ├── components/            # generic UI: Button, Table, Modal, StatusBadge
│   │   ├── hooks/
│   │   └── types/
│   ├── features/
│   │   ├── evidence/
│   │   │   ├── api.ts               # evidenceApi.list/upload/download/delete
│   │   │   ├── hooks.ts             # useEvidence(entityType, entityId), useUploadEvidence()
│   │   │   ├── components/
│   │   │   │   └── AttachmentsPanel.tsx  # reused inside Policy/Procedure/RiskItem detail views
│   │   │   └── __tests__/
│   │   ├── policies/
│   │   │   ├── api.ts              # policiesApi.list(), .get(), .create() ...
│   │   │   ├── hooks.ts            # usePolicies(), usePolicy(id), useCreatePolicy()
│   │   │   ├── components/         # PolicyList, PolicyForm, PolicyDetail
│   │   │   ├── types.ts
│   │   │   └── __tests__/
│   │   ├── procedures/             # mirrors policies/
│   │   ├── ai-systems/
│   │   │   ├── api.ts, hooks.ts, components/, types.ts, __tests__/
│   │   └── risk-assessments/
│   │       ├── api.ts, hooks.ts
│   │       ├── components/
│   │       │   ├── RiskAssessmentForm.tsx
│   │       │   ├── RiskMatrix.tsx       # likelihood x impact heatmap widget
│   │       │   └── RiskItemTable.tsx
│   │       └── __tests__/
│   ├── pages/                      # route-level compositions of feature components
│   │   ├── DashboardPage.tsx
│   │   ├── PoliciesPage.tsx
│   │   ├── ProceduresPage.tsx
│   │   ├── AISystemInventoryPage.tsx   # lists/creates AI Systems (feature folder stays `ai-systems/`)
│   │   └── RiskAssessmentsPage.tsx     # always entered via an AI System's detail page
│   └── main.tsx
├── tests/setupTests.ts
├── vite.config.ts
└── package.json
```

Each `features/<x>/api.ts` is the **only** place that knows the backend URL shape
for that feature; components never call `fetch` directly. This is what lets the
backend evolve independently and lets each feature be unit-tested by mocking one
file.

`AttachmentsPanel` is the one deliberately shared, cross-feature component (it
lives in `features/evidence/` since it owns the evidence API calls, but is
imported into `PolicyDetail`, `ProcedureDetail`, and `RiskItemTable` rows) —
a single upload/list/delete widget parameterized by `entityType` + `entityId`.

### 5.2 State management

- **Server state** (everything from the API): TanStack Query — handles caching,
  loading/error states, refetch-on-mutation invalidation. No Redux needed for MVP.
- **Local/UI state**: component-local `useState`/`useReducer` (e.g. form drafts,
  modal open/closed).
- **Forms**: `react-hook-form` + `zod` schema validation, with the zod schema
  shared/mirrored against backend Pydantic validation rules to avoid drift.

### 5.3 Testing strategy (frontend)

- **Unit tests**: Vitest + React Testing Library, one `__tests__` folder per
  feature, colocated. Test hooks with mocked `api.ts` (via `msw` — Mock Service
  Worker — for realistic HTTP mocking), and test components for rendering/
  interaction (e.g. "submitting the risk item form calls the mutation with correct
  payload").
- **Integration/E2E** (light for MVP): a small Playwright smoke suite covering the
  golden paths — create policy → approve it; create AI system → run risk
  assessment → see it on dashboard. Not exhaustive; expand as features grow.

## 6. Cross-Cutting Concerns

- **Config**: `.env` files for both frontend (`VITE_API_BASE_URL`) and backend
  (`DATABASE_URL`, `SECRET_KEY`), loaded via `pydantic-settings` / Vite's built-in
  env handling. `.env.example` checked in, `.env` gitignored.
- **Migrations**: Alembic from day one, even though SQLite is the MVP store —
  this is what makes "swap SQLite for Postgres later" a config change rather than
  a rewrite.
- **Audit trail**: centralized in `audit_service`, called from every service
  mutation — directly supports ISO 42001's "documented information" and EU AI
  Act logging expectations without being a compliance feature bolted on later.
- **Framework tagging**: `FrameworkControl` lookup table + `framework_tags` on
  `RiskAssessment`/`Policy`/`Procedure` — lets the UI show "this policy covers
  ISO 42001 clause 5.2" without hardcoding regulatory text into application logic.
- **Error handling**: services raise typed domain exceptions
  (`NotFoundError`, `InvalidStatusTransitionError`); a single FastAPI exception
  handler maps these to HTTP status codes, so routers stay thin.

## 7. MVP Feature Checklist

- [ ] Policy CRUD + draft/review/approve workflow + version history
- [ ] Procedure CRUD + same workflow, optionally linked to a Policy
- [ ] AI System register (CRUD) with lifecycle stage and risk tier
- [ ] Risk Assessment: create against an AI System, add/edit risk items,
      likelihood × impact scoring, mitigation tracking, residual risk
- [ ] Risk matrix visualization (heatmap) per assessment
- [ ] Framework tag reference data (seeded ISO 42001 clauses + EU AI Act articles)
      and tagging UI on policies/procedures/assessments
- [ ] Evidence upload/list/download/delete, attachable to policies, procedures,
      risk assessments, and risk items (local filesystem storage)
- [ ] Audit log viewer (read-only) per entity, including evidence upload/delete events
- [ ] Dashboard: counts by status/risk tier, items needing review
- [ ] Basic single-user auth (username/password, local only)
- [ ] Unit + integration test suites for backend and frontend as described above
- [ ] Seed script with realistic demo data (a few AI systems, policies, assessments)

## 8. Suggested Build Order

1. Backend skeleton (`core/`, `main.py`, Alembic, health-check route) + CI test run
2. `Policy` vertical slice end-to-end (model → repo → service → router → tests)
   as the template for the rest
3. `Procedure` (copy the Policy pattern)
4. `AISystem` + `RiskAssessment`/`RiskItem` (the most novel domain logic — risk
   scoring, matrix)
5. `AuditLogEntry` wired into all services
6. `FrameworkControl` seed data + tagging
7. `Evidence` model/service/router (polymorphic attach to whichever entities exist
   by this point) + local storage handling
8. Frontend: shared shell/layout → Policies feature → Procedures → AI Systems →
   Risk Assessments → Evidence's `AttachmentsPanel` wired into each detail view
   (mirrors backend order so each slice has a working API to build against)
9. Dashboard page last, once other data exists to summarize

## 9. Future Extensions (post-MVP, enabled by this design)

- Additional frameworks (NIST AI RMF, SOC 2) — just more `FrameworkControl` seed
  rows + tags, no schema change
- Vendor/third-party AI risk module — new domain folder on both sides
- Evidence versioning (re-upload a corrected file while keeping history) and
  virus/malware scanning on upload
- Multi-user roles beyond admin/contributor/viewer, real auth (OAuth)
- Postgres swap (Alembic + repository pattern already isolate this)
- Notifications/reminders for policy review due-dates
- Export to PDF/Word for audit packages

---

Sources consulted for architecture guidance:
- [FastAPI Project Structure: Production Guide 2026](https://www.zestminds.com/blog/fastapi-project-structure/)
- [FastAPI Best Practices — Auth0](https://auth0.com/blog/fastapi-best-practices/)
- [How to Structure a Scalable FastAPI Project](https://fastlaunchapi.dev/blog/how-to-structure-fastapi)
- [The Best React js Architecture for 2026: Domain-Driven + Feature-Sliced Design](https://medium.com/@albert_barsegyan/the-best-react-js-architecture-for-2026-domain-driven-feature-sliced-design-87f6e25d13fe)
- [React Architecture Patterns and Best Practices for 2026](https://www.bacancytechnology.com/blog/react-architecture-patterns-and-best-practices)
- [ISO 42001 Requirements: The Clause-by-Clause Guide](https://www.konfirmity.com/blog/iso-42001-requirements)
- [ISO 42001 Requirements Explained Clause by Clause](https://www.infosectrain.com/blog/iso-42001-requirements-explained-clause-by-clause)
- [EU AI Act 2026 Updates: Compliance Requirements and Business Risks](https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks)
- [EU AI Act: obligations for high-risk AI systems](https://www.aoshearman.com/en/insights/ao-shearman-on-tech/zooming-in-on-ai-10-eu-ai-act-what-are-the-obligations-for-high-risk-ai-systems)
