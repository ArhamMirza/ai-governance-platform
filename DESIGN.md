# AI Governance Platform — Design Document

How the platform is built and why. This is a living document: it describes the code as
it stands, and where a decision was not obvious it says what was chosen and what it
costs. For how to run it see the [README](README.md); for what it does and doesn't
defend against see [SECURITY.md](SECURITY.md); for the browser extension in detail see
[extension/README.md](extension/README.md); for deployment see
[deploy/README.md](deploy/README.md).

Contents: [1 Purpose](#1-purpose-and-scope) · [2 Principles](#2-design-principles) ·
[3 Architecture](#3-architecture) · [4 Backend](#4-backend) · [5 Governance records](#5-governance-records) ·
[6 AI assistance](#6-ai-assistance) · [7 Governing staff use of AI](#7-governing-staff-use-of-ai-tools) ·
[8 Security](#8-security-architecture) · [9 Frontend](#9-frontend) · [10 Testing](#10-testing-and-quality) ·
[11 CI and deployment](#11-ci-and-deployment) · [12 Standards map](#12-where-the-standards-are-handled) ·
[13 Not built](#13-not-built-yet) · [14 Decisions](#14-decision-log)

## 1. Purpose and scope

A full-stack application that helps one organization run an AI management system in line
with **ISO/IEC 42001** (AI management systems) and the **EU AI Act**, and that goes a step
beyond record-keeping by governing how staff actually use AI tools.

It has two halves:

1. **The management system** — the records an auditor asks for: context, policies and
   procedures, an AI system inventory with a gated life cycle, impact and risk
   assessments, objectives, competence, communication, change planning, internal audits,
   management review, corrective actions, improvements, incidents, concerns, suppliers,
   evidence, and a Statement of Applicability. A compliance view computes, live, how well
   each clause, Annex A control and EU AI Act article is covered.
2. **AI-use governance** — a register of approved third-party AI tools (employees request,
   the Chief AI Governance Officer decides), data-loss-prevention rules, and a Chrome/Edge
   extension that blocks or warns on unapproved AI sites and stops sensitive text being
   pasted into AI chats, reporting only counts back.

Around both sits an optional **AI assistant** (search and chat over the record, plus
drafting help) that can read and propose but never change anything.

**One organization per deployment.** There is no multi-tenancy. It runs on one machine:
React frontend, FastAPI backend, a single SQLite file and local file storage, with local
ML models for search. The only external call is to an AI provider, and only if one is
configured.

**Status:** a portfolio project. It has not had an independent security review and is not
ready to hold a real organization's data; see [SECURITY.md](SECURITY.md).

## 2. Design principles

These recur throughout the code and explain most of its shape.

- **Computed live, never stored.** A control's compliance status, an AI system's stage
  gate, an objective's standing, a supplier's review date, an unanswered concern — all
  are derived from the underlying records every time they are read, by pure functions in
  `app/core/*_tracking.py` and friends. A status therefore cannot outlive the thing it
  depends on, and it reopens by itself when a record is deleted, retired or goes stale.
  There is no "mark as done" box to get out of step.
- **Default deny.** Every business route requires a signed-in internal user
  (`get_internal_user`, applied to the router in `main.py`); a router added later is
  closed to employees automatically. Employees reach only the staff portal, built from an
  allow-list of fields.
- **Segregation of duties in the service layer.** Nobody approves their own submission;
  the Chief AI Governance Officer (CAIGO) must be an administrator; two approvers racing
  on one record cannot both win (transitions restate the status they checked in the
  `WHERE` clause).
- **AI can read and propose, never act.** Every model call goes through one service. The
  assistant's tools are read-only by construction — no function exists that writes.
  Drafts are held on the server for a person to accept or discard.
- **Untrusted content stays untrusted.** Anything a person typed or uploaded is delivered
  to a model inside a tagged envelope with a per-request nonce, never concatenated into
  instructions (OWASP LLM01).
- **Privacy by construction.** The extension evaluates rules in the browser and reports
  counts only: no text, no URLs, no times, and only for sites in the tool catalogue.
  Once a day it also checks in (who, and which version) so coverage can be shown. The
  server's schema refuses any other field.
- **Failures leave a record.** Indexing a document, drafting, extension sync: each ends in
  a recorded outcome rather than an exception that loses the source.
- **One place for each rule.** Reference data (controls, roles, impact factors), scoring,
  schedules and the approval chain each live in one module that everything else imports.

## 3. Architecture

```
 Browser (staff)              Browser (admin/contributor)
 ┌──────────────────┐         ┌───────────────────────────────────────┐
 │ Chrome / Edge     │         │  React + TypeScript + Vite             │
 │ extension (MV3)   │         │  TanStack Query · feature folders      │
 │ DLP checks, blocks│         │  Employee app (staff home) · main app  │
 └─────────┬────────┘         └──────────────────┬────────────────────┘
           │ Bearer key (counts,                 │ session cookie (JSON)
           │ policy via ETag)                    │
 ┌─────────▼─────────────────────────────────────▼────────────────────┐
 │ FastAPI                                                              │
 │ security headers · origin check · CORS · routers → services →        │
 │ repositories → SQLAlchemy models · Alembic migrations                │
 └───────┬──────────────────────┬──────────────────────┬──────────────┘
         │                      │                      │
   ┌─────▼──────┐        ┌──────▼───────┐       ┌──────▼─────────────┐
   │ SQLite      │        │ Evidence      │       │ Local ML models     │
   │ + FTS5      │        │ files on disk │       │ embeddings, rerank, │
   │ + sqlite-vec│        │ (UUID names)  │       │ OCR (ONNX, CPU)     │
   └────────────┘        └──────────────┘       └─────────────────────┘
                                                        │ optional
                                                 ┌──────▼──────────────┐
                                                 │ AI provider (LiteLLM)│
                                                 └─────────────────────┘
```

- **Two kinds of caller.** People use a session cookie; the extension has no session and
  presents the organization's enrollment key as a bearer token on `/api/v1/agent/*`,
  which sits outside the signed-in router and is excluded from the employee route walk by
  its own test.
- **Single process.** The API runs as one process; in-memory state (rate limits) assumes
  that. Sync endpoints run in FastAPI's threadpool, which is why `core/concurrency.py`
  exists (see §4.3).
- **Why SQLite.** One file holds records, the full-text index (FTS5) and the vector index
  (sqlite-vec), so search needs no second service and a backup is the database plus the
  uploads folder. The cost is no concurrent writers and backups you schedule yourself. Repositories isolate the engine, and
  Alembic is used from the start, so moving to PostgreSQL is a configuration and
  migration exercise rather than a rewrite (it is the first thing to do for real data).

## 4. Backend

### 4.1 Layers

`routers` (HTTP only) → `services` (business rules) → `repositories` (queries) →
`models` (SQLAlchemy), with `schemas` (Pydantic) at the edges and `core` for everything
pure and shared.

| Package | What lives there | Size |
|---|---|---|
| `app/routers` | Parse the request, call a service, return. Translate nothing: domain errors become HTTP statuses in one set of handlers in `main.py`. | 48 modules, ~320 operations |
| `app/services` | Business rules, orchestration, approvals, auditing. Never imports FastAPI. | 55 modules |
| `app/repositories` | Database access only; no rules. | 36 modules |
| `app/models` | ORM tables, one module per aggregate. | 50 modules |
| `app/schemas` | Request/response models; the extension's schemas refuse unknown fields. | 40 modules |
| `app/core` | Config, database, security primitives, and the **pure functions**: scoring, schedules, tracking, DLP rule validation, TOTP, passwords, prompts, chunking. | 43 modules |
| `alembic/versions` | Migrations; every migration is round-tripped (up, down, up) before it ships. | 54 |
| `app/seed.py` | Fictional demo data, written through the real service layer so audit history and computed values come out right. Refuses to run in production without `--allow-production`. | |
| `app/cli` | `python -m app.cli.index_documents` — drains the indexing queue. | |

**Rules enforced across the code:** routers never touch the ORM; services never import
`Request` or `HTTPException` (they raise `NotFoundError`, `ConflictError`,
`ValidationError`, `AuthenticationError`, `AuthorizationError`, `RateLimitedError`, which
`main.py` maps to 404/409/400/401/403/429, plus 503 for an unavailable dependency); every mutating service writes an
`AuditLogEntry`.

### 4.2 Configuration

`pydantic-settings`, from `.env`: `DATABASE_URL`, `EVIDENCE_STORAGE_DIR`, `SECRET_KEY`,
`CORS_ORIGINS`, `COOKIE_SECURE`, `ENVIRONMENT`, `SETUP_CODE`. With `ENVIRONMENT` set to
`production`/`staging` the app refuses to start on the example `SECRET_KEY`, on
`COOKIE_SECURE=false`, or with a wildcard CORS origin, switches off the API docs, and
requires a setup code for the first account.

### 4.3 Concurrency and consistency

Repositories commit as they write, so "read, find nothing, insert" spans two
transactions and two simultaneous requests can both insert. Unique constraints stop the
duplicate, and `core/concurrency.py` turns the loser's constraint violation into the row
the winner created (or the same `ConflictError` a sequential caller would get). State
transitions use `claim_transition`, restating the checked status in the `WHERE` clause.
Single-use secrets (TOTP time steps, recovery codes) are spent with one atomic `UPDATE`
whose row count says who won.

### 4.4 API conventions

REST under `/api/v1`, JSON in and out, OpenAPI at `/docs` in development only. Lists are
plain arrays; every create/update returns the record. Errors are `{"detail": "..."}`
with the status above. Uploads are multipart; exports are `.xlsx`. The session is an
HttpOnly cookie; there are no tokens in JavaScript.

## 5. Governance records

### 5.1 Two families of record

The original design split the records into two shapes, and both remain:

- **Documents** — a Policy or Procedure is a *folder of uploaded documents* moving
  through draft → in review → approved → retired, not text edited in the browser. `Folder`
  and `Evidence` (a polymorphic file attachment) are the substrate; the version counter
  bumps when the document set changes, and history is the audit log filtered to document
  actions (no separate version table). Evidence is validated centrally (allow-listed
  types, 25 MB cap, UUID storage names, deletion removes the file).
- **Sheets** — the AI System Inventory, Data Inventory and each Risk Assessment are
  spreadsheet-shaped: a `Sheet` with user-editable columns and `SheetRow`s of JSON.
  Users can upload an `.xlsx`/`.csv` or start blank, and export `.xlsx`. The one built-in
  formula is risk score (likelihood × impact, inherent and residual), computed by
  `sheet_service` and read-only. Everything else is a plain value.

Everything else is a small purpose-built aggregate (see 5.3).

### 5.2 Roles, permissions and approvals

Two separate systems decide what you can do:

| | |
|---|---|
| **Account role** (`User.role`) | `admin`, `contributor`, `viewer` — and `employee`, which holds *no* action and reaches only the staff portal. Actions: `view`, `edit`, `approve`, `manage_users`, `manage_settings`. One flat table in `core/permissions.py`. |
| **Governance role** (accountability) | Chief AI Governance Officer (capped at one holder, may have a time-boxed delegate, must be an admin), AI System Owner, Data Owner, Risk Owner, Implementation Team. Seed data in `core/governance_role_seed_data.py`. |

Approvals: the CAIGO signs off every dataset, every policy and procedure, every AI
system's release and retirement, and the final stage of impact and risk assessments.
Assessments run a **two-stage chain** (`approval_chain_service`): the AI System Owner
first (skipped if they did the assessment), then the CAIGO. No one approves their own
submission (`audit_service.require_different_approver`), and an AI system with no owner
cannot be submitted.

### 5.3 What each area does

| Area | Module(s) | Notes |
|---|---|---|
| Organization context (cl. 4) | `organization_context_service` | One record for the deployment; AI-drafted on request. |
| AI system inventory & life cycle | `ai_system_inventory_service`, `ai_system_lifecycle_service`, `lifecycle_gate_service` | Seven stages (ISO/IEC 5338 order); each stage has a gate computed from existing records; advance/revert are audited. |
| Impact assessments (cl. 8.4, A.5) | `impact_assessment_service` | Structured per ISO/IEC 42005: eight impact factors (`core/impact_factors.py`). |
| Risk (cl. 6.1) | `risk_assessment_service`, `risk_criteria_service`, `risk_scoring` | Configurable risk appetite; severity bands and the overdue rule live in `core/risk_scoring.py` so the dashboard, tables and filters agree. |
| Data inventory (A.7) | `data_inventory_service` | Sheet entries with a Data Owner and a review/approval step. |
| Objectives (6.2, 9.1) | `objective_service` | Measurements; standing is computed. |
| Changes (6.3) | `change_service` | Planned changes to the management system. |
| Competence (7.2, 7.3) | `competence_service` | Requirements and records. |
| Communication (7.4) | `communication_service` | Plan items and records; next-due is computed. |
| Internal audit (9.2) | `internal_audit_service` | Programs, audits, findings; configurable recurrence. |
| Management review (9.3) | `management_review_service` | Settings and meetings. |
| Corrective action & improvement (10.1, 10.2) | `corrective_action_service`, `improvement_service` | Flat records with computed standing. |
| Incidents (A.8.4, EU Art. 73) | `ai_incident_service` | Art. 73 reporting deadlines in `core/incident_reporting.py`. |
| Concerns (A.3.3) | `concern_service`, `staff_service` | Employees report; only administrators read. Reporter and handler sides are kept apart; triage timing is computed. |
| Suppliers (A.10.2–A.10.4) | `supplier_service` | Register, reviews, contract dates, links to AI systems. |
| AI tools (A.9.2) | `ai_tool_service` | See §7. |
| Statement of Applicability | `framework_service`, models `framework_soa_entry` | Per-control applicability with a justification. |
| EU AI Act applicability | `eu_ai_act_service`, `core/eu_ai_act_scope` | Whether and which articles apply; per-article overrides. |
| Dashboard | `dashboard_service` | One "needs attention" list grouped into areas; every count is computed. |
| Audit log | `audit_service` | Append-only; also the source of document version history and the sign-in trail. |

### 5.4 Framework mapping and compliance status

`FrameworkControl` holds the reference rows (24 ISO clauses, 38 Annex A controls, 24 EU AI
Act articles; `core/framework_reference_data.py`). Records are **tagged** to controls
(`FrameworkTag`, polymorphic by entity type and id). Suggestions come from the local
embedding model comparing a record's text with the roughly ninety controls by brute-force
cosine similarity — a closed-set classification, so deliberately not an LLM call and
independent of the vector index. `compliance_status_service` then computes, per control, one
of four states:

- **not applicable** — the Statement of Applicability or the EU applicability assessment
  excludes it, with the recorded justification (checked first);
- **no coverage** — nothing, or only deleted records, is tagged to it;
- **partial** — tagged, but at least one tagged record doesn't currently count (a draft or
  in-review document, an assessment not yet through its final approval, a retired record,
  an approved record past its review date);
- **satisfied** — every tagged record currently counts.

Each entity type has a small resolver (`_RESOLVERS`) saying what "currently counts" means.
What it deliberately does *not* do is judge whether a document's content satisfies a
clause: that is the human judgment made when tagging.

### 5.5 Audit trail

`audit_service.log(...)` is called from the service layer, never per router, so it cannot
be forgotten. Entries carry entity, action, actor and a JSON diff. They also record
sign-ins, failures, lockouts, password and two-step changes, changes to the extension's
enrollment key and settings, and AI tool decisions.

## 6. AI assistance

Optional and provider-neutral. `ai_assist_service` is the only code that talks to a model,
via LiteLLM, for Anthropic, OpenAI, Gemini, Groq or a local server. The organization's
provider key is stored encrypted (Fernet, key derived from `SECRET_KEY`), a daily token
budget is enforced and usage is accounted, and nothing here can write a record.

**Search** (`document_index_service`, `retrieval_service`). Records and uploaded documents
go through one pipeline: extract or render → scan → chunk → embed. Text lives in
`document_chunks`, an FTS5 mirror and a sqlite-vec table, all written in one place. Search
runs keyword (BM25) and vector retrievers and fuses their rankings, because each covers
the other's failure (an exact control id versus a question phrased unlike the document).
A local cross-encoder then reranks the top candidates. Embeddings are
`BAAI/bge-small-en-v1.5` (384 dimensions) and the reranker is
`Xenova/ms-marco-MiniLM-L-6-v2`, both ONNX on CPU; OCR (`rapidocr`) reads images and
scans. Vector search is optional: where sqlite-vec can't load, search falls back to
keywords alone.

Two properties matter more than ranking. **Returning nothing is a valid answer:** a
result must clear a relevance floor, so the assistant can say the record doesn't cover
something. **What could not be searched is reported:** a document that failed to index is
flagged, so "nothing found" is never confused with "could not look".

**Keeping the index current** (`core/index_hooks.py`). A session listener queues any
record whose text changed, in the same transaction as the change, so no future service can
forget. `index_queue` is drained in the background or by the CLI.

**The assistant** (`assistant_service`). One turn: rewrite a follow-up into a standalone
query; retrieve (plus the record the conversation was opened on, read in full); assemble a
cacheable system prompt, a rolling summary, recent turns and the sources, each inside a
nonce-tagged envelope; answer, using only **read-only tools** (`core/agent_tools.py`, which
compute exact counts the same way the dashboard does); then **verify before anyone sees
it** — every `[S#]` citation must name a source that was supplied, with one retry, and the
answer is checked for the turn's nonce. Nothing streams: showing an answer only after its
citations are checked is worth the wait in a governance tool.

**Prompt-injection defences, in order of how much they carry** (`core/ai_prompting.py`):
no dangerous capability exists; untrusted text is structurally separated and nonce-tagged;
the system prompt says envelope contents are data; and every chunk is *scanned* for text
that reads as an instruction, recorded on the chunk and never removed (a governance tool
legitimately holds documents *about* prompt injection).

**Drafting.** Whole-record drafts (organization context, impact assessments, policy and
procedure text, risk-item suggestions) are held server-side as `AiDraft`s for a person to
review; accepting one goes through the normal edit permission and audit.

## 7. Governing staff use of AI tools

A second half of the product, added after the records. See
[extension/README.md](extension/README.md) for the extension in full.

**Register and requests** (`ai_tool_service`). A catalogue of well-known AI sites ships in
`core/ai_tool_catalog_data.py` (twelve to start). Each tool has a status (catalogued,
approved, restricted or revoked; a site that is not approved is treated as unapproved), the
**most sensitive data class it may be given** (public, internal or confidential), domains,
conditions and a review date. A tool also has a **kind**: a website or web app, a desktop
app, a model run on the organization's own machines, an editor plugin or a browser
extension. Only a web tool has domains, and only web tools are sent to the browser
extension; the rest are governed by being on the register, approved with conditions
(for example "llama3.3 8B only, installed by IT, bound to localhost") and a review date,
while whoever manages the computers installs only what is approved. The platform does
not detect or block a local app: that needs software on the machine, which is IT's
(see the decision log).
Employees request a tool from the staff home; the CAIGO approves or rejects with a note,
and nobody decides their own request. Domain matching is by whole label
(`chatgpt.com.evil.net` is not `chatgpt.com`), with punycode handled and the most specific
domain winning (`core/ai_tool_domains.py` on the server, `policy.ts` in the extension).

**Data rules (DLP)** (`core/dlp_rules.py`, `frontend/src/shared/dlp/detectors.ts`). Built-in
detectors (card numbers with a Luhn check, IBANs with mod-97, SSN, NINO, CNIC, API keys,
private keys, JWTs, password assignments), keyword lists and custom regexes, each with a
data class and an action: monitor, warn or block. A rule applies only if its class is more
sensitive than the tool is cleared for; unapproved tools are treated as public-only. Rules
are *evaluated in the browser*; the same detector library powers the rule tester in the UI
and the extension, and a backend test checks the built-in keys match. Custom regexes are
validated for safety (no nested repeats, back-references, look-behind or empty matches).

**Settings, key, usage** (`ai_usage_service`). Settings choose what happens at an
unapproved site (**block by default**), how long counts are kept (90 days) and the notice
staff read. One enrollment key for the organization is shown once and stored as a SHA-256
hash; failures are rate limited. Usage events are daily aggregates
`(user, day, domain, event type, rule, action, count)` and nothing else.

**Coverage and overrides.** The extension checks in once a day (`POST /agent/checkin`:
email and version, nothing else), which keeps one row per person holding the last day it
reported. The Usage page compares that with the active accounts and lists whose browser
has never reported or has gone quiet for seven days; check-ins from an address that
matches no account are counted but not named. Going ahead past a warning is already a
recorded action (`overridden`); the Usage page totals it by site and person, and the
dashboard raises it, and any gap in coverage once a key has been issued, as attention
items. There is no email: an alert is a line on the dashboard.

**The extension** (`extension/`, Manifest V3, one build for Chrome and Edge). The service
worker fetches the policy (with ETag), applies it as `declarativeNetRequest` redirects for
unapproved domains, registers the checking script *only* on catalogued domains, and sends
counts every five minutes. The content script intercepts paste, Enter-to-send, send/submit
clicks, form submits and text-file uploads in the capture phase, runs the same detectors
and warns, blocks or counts. It fails open until it has a first policy and then keeps the
last good one. It is verified in real Chrome and Edge against a running platform
(51 checks each), and its limits are documented honestly: it covers only browsers it is
installed in, must be force-installed to be binding, checks text patterns rather than
meaning, and replayed events are untrusted.

## 8. Security architecture

The headline controls; [SECURITY.md](SECURITY.md) lists limits and
[deploy/README.md](deploy/README.md) the production settings.

- **Passwords** — PBKDF2-HMAC-SHA256, 600,000 iterations, stdlib only. Twelve characters
  minimum, refused if common (even dressed up), a keyboard run, near-constant, or built
  from the person's name or email; last five not reusable. Admin-created and reset
  passwords are temporary and force a change; one nobody has used stops working after
  seven days (`temporary_password_expires_at`; accounts that predate it are unaffected).
- **Sessions** — opaque random token in an HttpOnly, `SameSite=Strict` cookie (`__Host-`
  prefixed when secure); only its SHA-256 is stored; 14-day lifetime; ended everywhere on
  password change/reset, role change or deactivation.
- **Lockout and limits** — five wrong passwords lock an account for 15 minutes; 20 failures
  from one address block it; wrong codes, wrong current passwords and wrong setup codes
  are limited separately. In memory, one process.
- **Two-step sign-in** (`totp`, `mfa_service`, `mfa_ticket`) — RFC 6238 in the standard
  library (verified against the RFC vectors). A correct password yields only a five-minute
  signed ticket tied to the password; a code or one of ten single-use recovery codes
  completes it. Secrets are encrypted at rest, recovery codes hashed, codes spent
  atomically, five wrong codes lock the codes and re-entering the password does not
  reset that. An organization setting can require it of administrators (off by default;
  can only be switched on by an administrator who has it).
- **Web layer** (`core/web_security.py`) — headers on every response (nosniff, frame deny,
  referrer, permissions, a sandboxing CSP for the API, `no-store`, HSTS when secure), a
  cross-site request check for cookie-bearing state changes, an explicit CORS allow-list.
- **First account** — needs a setup code printed in the server log (or `SETUP_CODE`) on a
  real deployment.
- **Email addresses** (`core/email_address.py`) — one rule for account creation, first
  registration, the CSV import and the extension's reports: it catches typos (`bob@x`,
  `bob@@company.com`) but not fakes, and there is no verification, because the platform sends
  no email and accounts are created only by administrators. Addresses are stored trimmed and
  lowercased. Proving a mailbox belongs to a person needs email sending (not built).
- **Importing people** (`user_import_service`) — *Users → Import from CSV* takes `name`,
  `email` and an optional `role`. A preview says what each line would do and changes
  nothing; the import then works the file out again rather than trusting the preview.
  Matching is on email, so the same file twice does nothing. New accounts get a random
  starting password, returned once (never stored readably, never in the audit trail).
  A file can never create or change an administrator, change your own account, bring back
  a deactivated one, or deactivate anybody: people missing from the file are only listed.
  Capped at 200 people a file, because each new account costs a deliberately slow hash.
- **Backup and restore** (`app/backup.py`) — one command makes a `.tar.gz` holding a
  consistent copy of the database (SQLite's online backup, so the API keeps running), every
  upload and a manifest of SHA-256 checksums, then verifies it. Restore checks the archive,
  unpacks only the names this tool writes (nothing can land outside the target) and only
  into a folder that does not exist yet. Uploads are found by stored name under
  `EVIDENCE_STORAGE_DIR` (`core/evidence_files.py`), not by the full path the database once
  recorded, so a restore into another folder or machine still serves its files. Archives
  are not encrypted and do not hold `SECRET_KEY`; scheduling and off-machine copies are the
  operator's (deploy/README.md).
- **Secrets at rest** — AI provider keys and TOTP secrets under Fernet; the enrollment key
  and session tokens as hashes.
- **Access** — default deny, a test that walks every route as an employee, segregation of
  duties in services. Uploaded files are served as attachments, `nosniff`, sandboxed.
- **Supply chain** — `pip-audit`, `npm audit`, Dependabot, CodeQL and secret scanning;
  actions pinned; the built frontend is checked in CI for a strict Content-Security-Policy.

## 9. Frontend

React 19, TypeScript, Vite, TanStack Query v5, react-router, react-hook-form with zod,
plain CSS with design tokens (light and dark, following the OS unless pinned; the
pre-paint theme script is a separate file so a strict CSP can forbid inline script).

```
frontend/src/
├── app/            App.tsx (gates + app split), routes.tsx, Layout.tsx, queryClient.ts
├── shared/         api/httpClient + readError, components/, dlp/detectors.ts, hooks, theme
├── features/<x>/   api.ts · hooks.ts · types.ts · components/ · __tests__/   (40 features)
└── pages/          route-level compositions (47)
```

- **A feature owns its API.** `features/<x>/api.ts` is the only place that knows the URL
  shape; components never call `fetch`. Tests mock one file.
- **Server state in React Query**, UI state in components. A 401 is data ("not signed
  in"), not an error, so a background refetch can't swap the sign-in form for a spinner.
- **Gates before the app.** `AuthGate` decides what to show: sign-in (with the code step
  if the account has two-step), first-run setup (with the setup code when required), and —
  for someone signed in — a forced new password or a forced two-step set-up. Only when
  none applies does `App` choose between the **employee app** (a separate route tree for
  the `employee` role, so none of the platform renders for them) and the main app.
- **Shared, cross-feature pieces** are deliberately few: `DocumentBrowser` (folders and
  files, embedded in policies, procedures and AI system documents), `DataGrid` (the sheet
  editor), status badges and the confirm dialog.
- **Forms** use zod, with the server's rule text surfaced verbatim (password reasons, code
  errors) rather than a generic failure.
- **Accessibility and honesty in the UI.** Labels are associated, errors use `role="alert"`,
  and screens that show something once (temporary passwords, recovery codes) cannot be
  dismissed by accident.

## 10. Testing and quality

- **Backend** — about 2,000 pytest tests: unit tests of pure functions and services, and
  integration tests through `TestClient` against a fresh in-memory SQLite per test.
  Sign-in flows are tested through the real cookie flow, because the shortcut that
  overrides the session dependency would bypass exactly what is being tested. Time-based
  code takes an injected clock.
- **Frontend** — about 800 Vitest + Testing Library tests. Screens that depend on how
  data refreshes underneath them also have tests with the *real* hooks and query cache
  against a fake server (a bug of this kind slipped past tests that mocked the hooks).
- **Extension** — about 180 unit tests, plus a real-browser test that loads the built
  extension into Chrome and Edge and drives a running platform and a stub chat page.
- **Mutation testing, by hand, on the rules that matter** — deliberately change one thing
  (a threshold, a comparison, a removed check) and confirm a test fails. Survivors become
  tests or are explained as redundant. Used on password and lockout rules, session
  revocation, the TOTP/ticket/recovery code, the extension's decide/sync rules, DLP and
  the web-security middleware. It isn't in CI.
- **Migrations** — each is run up, down and up again; `alembic check` confirms models and
  migrations agree.
- **Lint and types** — `ruff` for Python; `oxlint` and `tsc -b` for the frontend and
  extension.

## 11. CI and deployment

- **CI** (`.github/workflows/ci.yml`; Python 3.11, Node 22): three jobs on every PR and push to `main` —
  backend (ruff, pip-audit, pytest with coverage), frontend (oxlint, npm audit, vitest,
  production build, the CSP check on the built page), extension (oxlint, npm audit,
  vitest, build). `main` is protected: changes arrive by pull request with those checks
  green. Separate workflows run CodeQL and a secret scan, and tagged releases create a
  GitHub Release.
- **Deployment** is by hand: `deploy/` has Caddy and nginx examples (https, strict CSP,
  HSTS, real client address forwarded), and `deploy/README.md` lists the settings and the
  uvicorn flags. There is no container setup yet.
- **The extension** is built with `npm run build` into `extension/dist`; rollout by
  force-install policy (Chrome and Edge) is described in its README.

## 12. Where the standards are handled

**ISO/IEC 42001 clauses**

| Clause | Where in the app |
|---|---|
| 4 Context | Organization context; AI roles (stakeholders) |
| 5 Leadership | Policies; governance roles (the CAIGO) |
| 6.1 Risk and opportunity | Risk assessments and risk criteria |
| 6.2 Objectives | AI objectives and their measurements |
| 6.3 Planning of changes | Management-system changes |
| 7.2, 7.3 Competence, awareness | Competence requirements and records |
| 7.4 Communication | Communication plan and records |
| 7.5 Documented information | Policies, procedures and evidence, with approval and audit history |
| 8 Operation | Impact assessments, the AI system life cycle and its gates, the data inventory |
| 9.1 Monitoring | Objective measurement; the dashboard |
| 9.2 Internal audit | Audit programs, audits and findings |
| 9.3 Management review | Management review settings and meetings |
| 10.1, 10.2 Improvement, nonconformity | Improvements; corrective actions |

**Annex A topics**

| Annex A topic | Where in the app |
|---|---|
| A.2 Policies related to AI | Policies and procedures |
| A.3 Internal organization (reporting concerns, A.3.3) | Governance roles; concerns |
| A.5 Assessing impacts of AI systems | Impact assessments |
| A.6 AI system life cycle | Life cycle stages and gates |
| A.7 Data for AI systems | Data inventory |
| A.8 Information for interested parties (incident reporting, A.8.4) | AI incidents |
| A.9 Use of AI systems (A.9.2) | The AI tool register, DLP rules and the extension |
| A.10 Third-party relationships (A.10.2–A.10.4) | Suppliers |

**EU AI Act.** The applicability assessment decides which articles apply to the
organization, with per-article overrides and a recorded reason. Serious-incident reporting
deadlines (Art. 73) are built into incidents. All 24 articles ship as controls that records
are tagged against.

**Coverage is whatever the records are tagged to**, judged current by the rules in §5.4 —
the app does not claim a clause is met because a feature exists.

## 13. Not built yet

- Packaged extension rollout files; a hardware-key (WebAuthn) second factor.
- Evidence packs (PDF/Word/ZIP) for auditors; more tagging so the compliance numbers
  reflect work done.
- A dedicated concerns-officer role; single sign-on; email (so new accounts get starting
  passwords handed over rather than a set-up link).
- PostgreSQL, backups the app schedules and monitors itself (the command exists; see §8),
  a container setup, encryption at rest, a session idle
  timeout, a sandboxed document parser, and an independent security review.
- In-app spreadsheet formulas beyond the risk score; multi-tenancy.

## 14. Decision log

| Decision | Why | Cost |
|---|---|---|
| Layered FastAPI (routers → services → repositories) | Services are unit-testable without HTTP; repositories isolate the engine. | More files than a flat app. |
| Documents as folders of uploads; sheets as JSON rows | Organizations already have documents and spreadsheets; the app consolidates them instead of replacing them. | No in-app authoring or formulas. |
| Status computed live, not stored | Cannot drift from the records it depends on. | Every read does the work; fine at this scale. |
| SQLite + FTS5 + sqlite-vec | One database file, a command for consistent backups, no extra service. | Single writer; PostgreSQL is the step for real use. |
| Local embeddings, reranker and OCR | Nothing leaves the machine to search evidence. | A larger install and a CPU cost at indexing. |
| No streaming answers | Citations are verified first; streaming would show unverified text. | A short wait. |
| Read-only AI tools | A successful prompt injection yields a wrong sentence, not a governance decision. | The assistant cannot take an action for you. |
| DLP evaluated in the browser, counts only | Text never reaches the server; the extension cannot become a browsing log. | The server cannot audit what was caught beyond counts. |
| Block-by-default for unapproved AI sites | An override should be a decision, not the default. | More requests to the CAIGO. |
| Standard-library crypto for passwords and TOTP | Few dependencies to audit; both are small, well-specified algorithms. | PBKDF2 rather than argon2id. |
| One deployment, one organization | Keeps access control simple and auditable. | No hosted multi-customer mode. |
| Local and desktop AI is governed by approval, not detected or blocked | The browser extension cannot see native apps, and blocking inside them needs software on the machine (endpoint DLP, run by whoever manages the computers), which is a different product with a much larger privacy footprint. A gateway in front of local model servers is the likely next step. | A local tool nobody reported stays invisible. |

---

Sources consulted for the original architecture guidance:
- [FastAPI Project Structure: Production Guide 2026](https://www.zestminds.com/blog/fastapi-project-structure/)
- [FastAPI Best Practices — Auth0](https://auth0.com/blog/fastapi-best-practices/)
- [How to Structure a Scalable FastAPI Project](https://fastlaunchapi.dev/blog/how-to-structure-fastapi)
- [The Best React js Architecture for 2026: Domain-Driven + Feature-Sliced Design](https://medium.com/@albert_barsegyan/the-best-react-js-architecture-for-2026-domain-driven-feature-sliced-design-87f6e25d13fe)
- [React Architecture Patterns and Best Practices for 2026](https://www.bacancytechnology.com/blog/react-architecture-patterns-and-best-practices)
- [ISO 42001 Requirements: The Clause-by-Clause Guide](https://www.konfirmity.com/blog/iso-42001-requirements)
- [ISO 42001 Requirements Explained Clause by Clause](https://www.infosectrain.com/blog/iso-42001-requirements-explained-clause-by-clause)
- [EU AI Act 2026 Updates: Compliance Requirements and Business Risks](https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks)
- [EU AI Act: obligations for high-risk AI systems](https://www.aoshearman.com/en/insights/ao-shearman-on-tech/zooming-in-on-ai-10-eu-ai-act-what-are-the-obligations-for-high-risk-ai-systems)
