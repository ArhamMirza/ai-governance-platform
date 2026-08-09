# AI Governance Platform — MVP Design Document

## 1. Purpose & Scope

A locally-run, full-stack application to help an organization manage AI governance
activities in line with the **EU AI Act** and **ISO/IEC 42001** (AI Management
System standard). The MVP focuses on four pillars, split across two different
interaction models:

**Document consolidation** (Policies, Procedures) — for MVP, the goal is *not* an
in-app authoring/editor experience. It's a place to organize and centralize
existing governance documents that already exist elsewhere (Word docs, PDFs,
scanned sign-offs). A Policy/Procedure is a **folder of uploaded documents** moving
through a draft/review/approve workflow — not a markdown document being edited in
the browser. An AI-assisted policy drafting/editing experience is an explicit
**post-MVP** feature (see §9) once the consolidation workflow is solid.

**Spreadsheet-based data** (AI System Inventory, Risk Assessments) — rather than
fixed web forms with a rigid schema, these are **sheet-backed**: a user can either
upload an existing `.xlsx`/`.csv` (their current inventory/risk register) or start
a blank one, and edit it in-app as a data grid with the columns they actually use.
The uploaded/edited data is parsed into structured rows so it stays queryable, but
the *interaction model* is "spreadsheet", not "form". AI-assisted sheet generation
is an explicit **post-MVP** feature (see §9).

1. **Policy Management** — organize policy documents into folders, move each
   Policy through a draft/review/approve/retired workflow. Policies are
   **organization-wide**: they do not reference any specific AI System.
2. **Procedure Management** — same folder + workflow model as Policies. Also
   **organization-wide**, with no link to specific AI Systems; a Procedure may
   optionally link to the Policy it implements.
3. **AI System Inventory** — a single, organization-wide **spreadsheet**: each row
   is an AI system/use-case, columns are its attributes (name, purpose, lifecycle
   stage, risk tier, etc.), uploadable/editable/exportable as a sheet.
4. **AI Risk Assessment** — performed **against a specific AI System** (one row in
   the inventory sheet); each assessment is its own **spreadsheet** of risk items
   (likelihood, impact, mitigation, residual risk), uploadable/editable/exportable.
5. **Evidence & Document Management** — the underlying file-storage/organization
   system. Policy/Procedure folders are *built on* this (see §4.2); it also
   supports attaching supporting files to Risk Assessments/Risk Items as proof of
   compliance activity.

In short: Policies and Procedures live above the AI System Inventory (they govern
the organization as a whole); Risk Assessments live below it (each one is scoped
to one row in the inventory sheet).

Everything else (auditing trails, dashboards, compliance mapping) supports these
pillars. The system runs entirely locally: React frontend, FastAPI backend,
SQLite database, local filesystem storage — no external services required for the MVP.

### Out of scope for MVP (explicitly deferred)
- Multi-tenant / multi-org support
- Authentication providers (SSO/OAuth) — MVP uses simple local auth (single admin
  user or basic username/password) since it runs locally
- **AI-assisted policy/procedure drafting and editing** — MVP is consolidation
  (folders + uploads) only; an in-app AI writing assistant is a named post-MVP goal
- **AI-assisted sheet generation** (e.g. "draft me a risk register") — MVP supports
  upload-an-existing-sheet or build-one-manually only
- In-app spreadsheet formulas/functions (SUM, VLOOKUP, etc.) — cells hold values,
  not formulas, for MVP; computed columns (like risk score) are computed by the
  app's business logic, not a general formula engine
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
│   │   ├── folder.py
│   │   ├── evidence.py
│   │   ├── sheet.py             # Sheet + SheetRow
│   │   ├── risk_assessment.py   # RiskAssessment header only; rows live in Sheet/SheetRow
│   │   └── audit_log.py
│   ├── schemas/                # Pydantic request/response models (mirrors models/)
│   │   ├── policy.py
│   │   ├── procedure.py
│   │   ├── folder.py
│   │   ├── evidence.py
│   │   ├── sheet.py
│   │   └── risk_assessment.py
│   ├── repositories/           # DB access only, no business rules
│   │   ├── policy_repository.py
│   │   ├── procedure_repository.py
│   │   ├── folder_repository.py
│   │   ├── evidence_repository.py
│   │   ├── sheet_repository.py
│   │   └── risk_assessment_repository.py
│   ├── services/                # Business logic, orchestration, validation rules
│   │   ├── policy_service.py
│   │   ├── procedure_service.py
│   │   ├── folder_service.py
│   │   ├── evidence_service.py   # validates file type/size, writes to storage, bumps Policy/Procedure version
│   │   ├── sheet_service.py       # column/row CRUD, xlsx/csv parse+export, risk-score computed column
│   │   ├── risk_assessment_service.py
│   │   └── audit_service.py
│   ├── routers/                 # HTTP layer only: parse request, call service, return
│   │   ├── policies.py
│   │   ├── procedures.py
│   │   ├── evidence.py
│   │   ├── ai_system_inventory.py
│   │   └── risk_assessments.py
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

The model splits into two families: **document entities** (Policy/Procedure, built
on Folder + Evidence) and **sheet entities** (AI System Inventory / Risk
Assessment, built on Sheet + SheetRow). Both share `AuditLogEntry` and
`FrameworkControl`.

#### Document family — Policy, Procedure, Folder, Evidence

| Entity | Key fields | Notes |
|---|---|---|
| `User` | id, name, email, role (`admin`, `contributor`, `viewer`) | Minimal RBAC for MVP |
| `Policy` | id, title, description, status (`draft/in_review/approved/retired`), version, owner_id, effective_date | Organization-wide; **no** AI System reference, **no** content field — a Policy is a folder of documents, not authored text |
| `Procedure` | id, title, description, status, policy_id (FK, optional link to a Policy), owner_id | Same shape and workflow as Policy |
| `Folder` | id, entity_type (`Policy`/`Procedure`), entity_id, parent_folder_id (FK, nullable, self-referential), name, created_at | Lets a Policy/Procedure organize its documents into a hierarchy (e.g. "Policy X" → "Signed Versions" → `2026-approval.pdf`). Root-level documents have no folder (`Evidence.folder_id` is null) |
| `Evidence` | id, entity_type (`Policy`/`Procedure`/`RiskAssessment`/`RiskItem`), entity_id, folder_id (FK, nullable), filename, content_type, size_bytes, storage_path, description, uploaded_by, uploaded_at | Polymorphic file attachment — the same entity now serves both "the documents that make up a Policy" and "supporting evidence attached to a Risk Item"; `folder_id` only meaningful where Folder is used |

**Policy/Procedure versioning, reworked**: since there's no text content to diff,
`version` is a simple counter that increments whenever the document set changes
(a file is added, replaced, or removed) while status is `draft`. There's no
separate `PolicyVersion` table — full history is just the `AuditLogEntry` rows for
that Policy filtered to document-change actions (`document_added`,
`document_removed`), which the audit log already captures. One less table to keep
in sync, and it composes with the audit trail we already need for compliance
"documented information" requirements either way.

#### Sheet family — AI System Inventory, Risk Assessment

| Entity | Key fields | Notes |
|---|---|---|
| `Sheet` | id, entity_type (`AISystemInventory`/`RiskAssessment`), columns (JSON list of `{key, label, data_type}`), title, created_at, updated_at | Generic spreadsheet container. Columns are user-editable (add/remove/reorder), so each org's inventory/risk register can carry the fields they actually use |
| `SheetRow` | id, sheet_id (FK), row_index, data (JSON dict of `{column_key: value}`), created_at, updated_at | One row = one record (one AI system, or one risk item). Flexible schema via JSON keeps this generic without a column-per-field DB migration every time a user adds a column |
| `AISystemInventory` | *(singleton)* — exactly one `Sheet` with `entity_type="AISystemInventory"` exists per install, auto-created on first run with default columns (`name`, `description`, `purpose`, `lifecycle_stage`, `risk_tier`) | The org can add/remove columns beyond the defaults |
| `RiskAssessment` | id, ai_system_row_id (FK to `SheetRow.id` in the inventory sheet, **required**), sheet_id (FK, **required** — the assessment's own risk-item sheet), framework_tags (JSON list), status (`draft/in_progress/completed`), assessor_id, assessment_date, overall_risk_rating | Header record; always scoped to exactly **one** AI System (one row) from the inventory, same rule as before — just linked to a sheet row instead of an `AISystem` table row. Its risk items live in `sheet_id`'s rows, with default columns `category`, `description`, `likelihood`, `impact`, `mitigation`, `residual_likelihood`, `residual_impact`, `control_owner`, `status` |
| `AuditLogEntry` | id, entity_type, entity_id, action, actor_id, timestamp, diff (JSON) | Append-only trail — now also the source of Policy/Procedure version history (see above) |
| `FrameworkControl` (reference/lookup table) | id, framework (`ISO42001`/`EU_AI_ACT`), clause_ref, title, description | Static seed data used to populate the framework_tags picker — not user-editable in MVP |

**Risk scoring inside a sheet**: `sheet_service` recognizes the reserved column
keys `likelihood`/`impact` (and `residual_likelihood`/`residual_impact`) on a
`RiskAssessment`'s sheet and auto-computes `inherent_risk_score = likelihood *
impact` (and the residual equivalent) as a derived, read-only column whenever
those two cells are present on a row — this is the one place "spreadsheet" gets a
built-in formula, because it's the one calculation the compliance frameworks
actually care about. Everything else is a plain value cell. Overall assessment
rating rolls up from the max/average of its rows' computed scores.

**Upload/export**: both `AISystemInventory` and `RiskAssessment` sheets support
`POST .../upload` (parse an `.xlsx`/`.csv` into columns + rows, replacing or
merging into the sheet) and `GET .../export` (download the current sheet as
`.xlsx`), via `openpyxl` on the backend. This is also the seam where a future
"AI generates this sheet for me" feature plugs in later — it would just produce
the same upload payload a human-edited file would.

### 4.3 API surface (MVP)

REST, versioned under `/api/v1`, JSON in/out, OpenAPI docs auto-generated at `/docs`.

```
GET/POST         /api/v1/policies
GET/PUT/DELETE   /api/v1/policies/{id}          # PUT edits title/description/effective_date only
POST             /api/v1/policies/{id}/submit-for-review
POST             /api/v1/policies/{id}/approve
GET              /api/v1/policies/{id}/versions  # derived from audit log, see 4.2

GET/POST         /api/v1/procedures
GET/PUT/DELETE   /api/v1/procedures/{id}
... (same review/approve/version pattern as policies)

GET/POST         /api/v1/folders?entity_type=Policy&entity_id={id}&parent_folder_id={id?}
GET/PUT/DELETE   /api/v1/folders/{folder_id}
# Generic, not nested under /policies -- Procedure and any future document-bearing
# entity reuses the same endpoints rather than duplicating a folders sub-route per entity.

GET              /api/v1/ai-system-inventory                # the singleton Sheet + its rows
PUT              /api/v1/ai-system-inventory/columns         # add/remove/reorder columns
POST/PUT/DELETE  /api/v1/ai-system-inventory/rows[/{row_id}]
POST             /api/v1/ai-system-inventory/upload           # multipart .xlsx/.csv
GET              /api/v1/ai-system-inventory/export            # download .xlsx

GET/POST         /api/v1/risk-assessments                     # header records
GET/PUT/DELETE   /api/v1/risk-assessments/{id}
PUT              /api/v1/risk-assessments/{id}/columns
POST/PUT/DELETE  /api/v1/risk-assessments/{id}/rows[/{row_id}]
POST             /api/v1/risk-assessments/{id}/upload
GET              /api/v1/risk-assessments/{id}/export

GET              /api/v1/framework-controls?framework=ISO42001
GET              /api/v1/audit-log?entity_type=Policy&entity_id=...
GET              /api/v1/dashboard/summary   # counts by status/risk tier for home page

POST             /api/v1/evidence?entity_type=Policy&entity_id={id}&folder_id={id?}   # multipart upload
GET              /api/v1/evidence?entity_type=Policy&entity_id={id}&folder_id={id?}   # list at that level
GET              /api/v1/evidence/{id}/download
DELETE           /api/v1/evidence/{id}
```

Every mutating endpoint writes an `AuditLogEntry` via `audit_service` — this is
called from the service layer (not duplicated per-router) so it can never be
forgotten. For Policy/Procedure, `evidence_service` (upload/delete) is what
triggers the `version` counter bump and the `document_added`/`document_removed`
audit entries — the "versioning" and "file management" concerns live in the same
place rather than being synced between two systems.

`evidence_service.py` enforces MVP guardrails centrally: an allow-list of file
extensions/content-types, a max file size (e.g. 25 MB, configurable), and a
UUID-based storage filename (the original filename is kept only as metadata) to
avoid path-traversal or collision issues. Deleting an `Evidence` row also deletes
the underlying file — handled in the service, not the router, so it's covered by
unit tests without needing a running server.

`sheet_service.py` centralizes: column add/remove/reorder validation (can't remove
a reserved column like `likelihood` on a risk-assessment sheet without warning,
since it'd silently drop the risk-score calc), row CRUD, the `.xlsx`/`.csv`
parse-on-upload and generate-on-export logic, and the risk-score computed-column
behavior described in §4.2.

### 4.4 Testing strategy (backend)

- **Unit tests** (majority of coverage): test services with repositories replaced
  by fakes/mocks — pure business logic (status transitions, risk scoring, version
  bumping) with no DB or HTTP involved. Fast, run on every save.
- **Integration tests**: `TestClient` against routers, backed by a real SQLite
  DB created fresh per test session (file `:memory:` or temp file), verifying
  request/response contracts, status codes, and validation errors.
- `sheet_service` tests cover: column add/remove/reorder, row CRUD, the
  risk-score computed-column behavior (present/missing likelihood or impact),
  and round-tripping a small `.xlsx` through upload → parse → export to confirm
  no data loss.
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
│   │   │   ├── hooks.ts             # useEvidence(entityType, entityId, folderId?), useUploadEvidence()
│   │   │   ├── components/
│   │   │   │   └── DocumentBrowser.tsx  # folder tree + file list + upload; reused by Policy/Procedure
│   │   │   └── __tests__/
│   │   ├── policies/
│   │   │   ├── api.ts              # policiesApi.list(), .get(), .create() ...
│   │   │   ├── hooks.ts            # usePolicies(), usePolicy(id), useCreatePolicy()
│   │   │   ├── components/         # PolicyList, PolicyForm, PolicyDetail (embeds DocumentBrowser)
│   │   │   ├── types.ts
│   │   │   └── __tests__/
│   │   ├── procedures/             # mirrors policies/
│   │   ├── sheets/
│   │   │   ├── api.ts               # sheetsApi generic column/row/upload/export calls
│   │   │   ├── hooks.ts
│   │   │   ├── components/
│   │   │   │   └── DataGrid.tsx      # editable grid: columns, rows, add/remove, upload/export buttons
│   │   │   └── __tests__/
│   │   ├── ai-system-inventory/
│   │   │   ├── api.ts, hooks.ts, components/, types.ts, __tests__/   # thin wrapper around sheets/ for the singleton inventory sheet
│   │   └── risk-assessments/
│   │       ├── api.ts, hooks.ts
│   │       ├── components/
│   │       │   ├── RiskAssessmentHeader.tsx   # framework tags, status, linked AI system
│   │       │   └── RiskMatrix.tsx              # likelihood x impact heatmap, reads the DataGrid's rows
│   │       └── __tests__/
│   ├── pages/                      # route-level compositions of feature components
│   │   ├── DashboardPage.tsx
│   │   ├── PoliciesPage.tsx
│   │   ├── ProceduresPage.tsx
│   │   ├── AISystemInventoryPage.tsx   # renders the singleton inventory sheet via sheets/DataGrid
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

`DocumentBrowser` and `DataGrid` are the two deliberately shared, cross-feature
components. `DocumentBrowser` lives in `features/evidence/` (folder tree + file
list + upload, parameterized by `entityType`/`entityId`) and is embedded in both
`PolicyDetail` and `ProcedureDetail` — it *is* the Policy/Procedure editing
experience for MVP, not a side panel. `DataGrid` lives in `features/sheets/` and
is embedded in both the AI System Inventory page and each Risk Assessment's
detail page — same component, different `Sheet` behind it.

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

- [x] Policy CRUD + draft/review/approve workflow *(built with a text `content`
      field — needs reworking to drop content/PolicyVersion and add Folder, per
      §4.2's revised model)*
- [ ] Rework Policy to the folder/document model; wire `Folder` + `Evidence`
- [ ] Procedure CRUD, same folder/document model as Policy, optionally linked to
      a Policy
- [ ] `Evidence` model/service/router (polymorphic file storage) — needed by both
      the document family and as attachments on risk assessments/items
- [ ] `Folder` model/service/router + `DocumentBrowser` frontend component
- [ ] `Sheet`/`SheetRow` model/service/router: column CRUD, row CRUD, `.xlsx`/
      `.csv` upload-parse and export
- [ ] AI System Inventory: singleton `Sheet`, auto-created with default columns
- [ ] Risk Assessment: header record linked to one inventory row + its own
      `Sheet`; risk-score computed column (likelihood × impact, inherent +
      residual)
- [ ] `DataGrid` frontend component (shared by AI System Inventory and Risk
      Assessments) with inline edit, add/remove row & column, upload/export
- [ ] Risk matrix visualization (heatmap) reading a Risk Assessment's sheet rows
- [ ] Framework tag reference data (seeded ISO 42001 clauses + EU AI Act articles)
      and tagging UI on policies/procedures/assessments
- [ ] Audit log viewer (read-only) per entity, including document add/remove and
      evidence upload/delete events
- [ ] Dashboard: counts by status/risk tier, items needing review
- [ ] Basic single-user auth (username/password, local only)
- [ ] Unit + integration test suites for backend and frontend as described above
- [ ] Seed script with realistic demo data

## 8. Suggested Build Order

1. Backend skeleton (`core/`, `main.py`, Alembic, health-check route) + CI test
   run — **done**
2. `Policy` vertical slice, text-content version — **done**, now superseded
3. `Folder` + `Evidence` models/service/router (the shared file-storage
   substrate everything else in this list depends on)
4. Rework `Policy` onto Folder + Evidence: drop `content`/`PolicyVersion`, wire
   version-counter bump + audit-derived history, update the frontend to embed
   `DocumentBrowser` instead of a content textarea — this becomes the corrected
   template
5. `Procedure` (copy the reworked Policy pattern)
6. `Sheet`/`SheetRow` + `sheet_service` (column/row CRUD, upload/export, the
   risk-score computed column) — the most novel new subsystem
7. AI System Inventory (singleton sheet wrapper) + Risk Assessment (header +
   linked sheet)
8. `AuditLogEntry` wired into all services (already true for Policy/Evidence;
   extend to Folder/Sheet/RiskAssessment)
9. `FrameworkControl` seed data + tagging
10. Frontend: `DocumentBrowser` (Policies/Procedures) → `DataGrid` (AI System
    Inventory) → Risk Assessments (header UI + `DataGrid` + `RiskMatrix`)
11. Dashboard page last, once other data exists to summarize

## 9. Future Extensions (post-MVP, enabled by this design)

- **AI-assisted policy/procedure drafting and editing** — an in-app writing
  assistant that helps produce a document (not just store one). Natural next
  step once consolidation (this MVP) is in daily use
- **AI-assisted sheet generation** — "draft me a risk register for this AI
  system" producing a pre-filled `Sheet`. The upload/parse pipeline built for
  MVP is the same seam this would plug into
- Spreadsheet formulas beyond the built-in risk-score computed column
- Additional frameworks (NIST AI RMF, SOC 2) — just more `FrameworkControl` seed
  rows + tags, no schema change
- Vendor/third-party AI risk module — new domain folder on both sides
- Evidence/document versioning (re-upload a corrected file while keeping prior
  versions, not just replacing) and virus/malware scanning on upload
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
