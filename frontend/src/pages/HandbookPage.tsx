const SECTIONS = [
  { id: "roles", label: "Who does what" },
  { id: "lifecycle", label: "The AI system life cycle" },
  { id: "data-inventory", label: "The Data Inventory" },
  { id: "assessments", label: "Impact & risk assessments" },
  { id: "policies", label: "Policies & procedures" },
  { id: "archive", label: "Retiring a system" },
  { id: "evidence", label: "Evidence & documents" },
  { id: "frameworks", label: "Frameworks & the SoA" },
  { id: "management-system", label: "The rest of the management system" },
  { id: "ai-use", label: "Governing staff use of AI" },
  { id: "assistant", label: "The assistant" },
  { id: "dashboard", label: "Reading the dashboard" },
  { id: "account", label: "Your account & signing in" },
  { id: "bulk", label: "Editing in bulk, safely" },
  { id: "reference", label: "Quick reference" },
];

/** Mirrors LifecycleStageTracker's markup, but every stage renders "done" --
 * this is a reference diagram of the whole life cycle, not one system's
 * actual progress through it. */
function StageDiagram() {
  const stages = [
    "Inception",
    "Design",
    "Development",
    "Verification & Validation",
    "Deployment",
    "Operation & Monitoring",
    "Retirement",
  ];
  return (
    <ol className="stage-tracker" aria-label="Life cycle stages">
      {stages.map((label, index) => (
        <li key={label} className="stage-step is-done">
          <span className="stage-step-marker">{index + 1}</span>
          <span className="stage-step-label">{label}</span>
        </li>
      ))}
      <li className="stage-step is-current">
        <span className="stage-step-marker">↓</span>
        <span className="stage-step-label">Archive</span>
      </li>
    </ol>
  );
}

/** A stage gate exactly as StageGateChecklist renders one, with a fixed
 * requirement list instead of a live one -- this is what each stage's gate
 * asks for, not any particular system's current status against it. */
function GateReference({
  stage,
  ordinal,
  intro,
  requirements,
}: {
  stage: string;
  ordinal: string;
  intro: string;
  requirements: { label: string; detail: string }[];
}) {
  return (
    <div className="stage-gate">
      <div className="page-header" style={{ marginBottom: 2 }}>
        <h3>{stage}</h3>
        <span className="gate-detail" style={{ whiteSpace: "nowrap" }}>{ordinal}</span>
      </div>
      <p>{intro}</p>
      <ul className="gate-requirements">
        {requirements.map((req) => (
          <li key={req.label} className="is-satisfied">
            <span className="gate-marker" aria-hidden="true">✓</span>
            <span>
              <strong>{req.label}</strong>
              <span className="gate-detail">{req.detail}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function HandbookPage() {
  return (
    <section className="handbook">
      <div className="page-header">
        <div>
          <h1>Governance Handbook</h1>
          <p className="handbook-lede">
            The operating manual for this platform: what each role is accountable for, what has
            to happen before an AI system can move to its next stage, how a dataset, an
            assessment, or a policy earns its sign-off, and how staff use of AI tools is governed. It follows ISO/IEC 42001&rsquo;s own
            structure &mdash; nothing here is enforced by convention alone; every rule below is a
            gate the platform actually checks.
          </p>
        </div>
      </div>

      <nav className="handbook-toc" aria-label="Handbook sections">
        {SECTIONS.map((s) => (
          <a key={s.id} href={`#${s.id}`} className="framework-tag-chip">{s.label}</a>
        ))}
      </nav>

      <section id="roles">
        <h2 style={{ marginTop: 36 }}>Who does what</h2>
        <p>
          Two separate systems decide what you can do. Your <strong>account role</strong> (set by
          an admin, in Users) controls what you can touch in the app at all. Your{" "}
          <strong>governance role</strong> (assigned in Roles &amp; Responsibilities) says what
          you&rsquo;re personally accountable for &mdash; an AI system, a dataset, a risk. Most
          actions need both: edit rights <em>and</em> being the right person.
        </p>

        <h3 style={{ marginTop: 22 }}>Account roles</h3>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Role</th><th>Can do</th></tr></thead>
            <tbody>
              <tr><td>Viewer</td><td>Read everything. Can&rsquo;t create, edit, or approve anything.</td></tr>
              <tr><td>Contributor</td><td>Everything Viewer can, plus create and edit records &mdash; rows, documents, draft assessments, folders. Cannot approve anything gated on Chief AI Governance Officer, and cannot manage users or org-wide settings.</td></tr>
              <tr><td>Admin</td><td>Everything, including approving as Chief AI Governance Officer (if assigned that governance role), managing user accounts, and setting the organization&rsquo;s risk appetite.</td></tr>
              <tr><td>Employee</td><td>Not an internal user: a login for staff who use AI tools but not this platform. It reaches only the <strong>staff home</strong> &mdash; the policies and procedures shared with staff, a way to report a concern, and a way to ask for an AI tool. Every other page is closed to it.</td></tr>
            </tbody>
          </table>
        </div>

        <h3 style={{ marginTop: 26 }}>Governance roles</h3>
        <p style={{ marginBottom: 6 }}>
          Assigned per person in <strong>Roles &amp; Responsibilities</strong>, and shown against
          their name everywhere they&rsquo;re accountable for something.
        </p>
        <div className="governance-role-grid">
          <div className="governance-role-card">
            <h3><span className="handbook-role-dot" style={{ background: "var(--primary)" }} /> Chief AI Governance Officer</h3>
            <p style={{ fontSize: 13 }}>
              The organization&rsquo;s approver. Signs off every dataset, every impact and risk
              assessment&rsquo;s final stage, every policy and procedure, and every AI
              system&rsquo;s release and retirement. Capped at one holder &mdash;{" "}
              <a href="#delegate">a time-boxed delegate can stand in</a> when they&rsquo;re away.
            </p>
          </div>
          <div className="governance-role-card">
            <h3><span className="handbook-role-dot" style={{ background: "var(--success)" }} /> AI System Owner</h3>
            <p style={{ fontSize: 13 }}>
              Accountable for one AI system across its whole life cycle. Approves the first stage
              of its impact and risk assessments &mdash; unless they did the assessment
              themselves, in which case it goes straight to the Chief AI Governance Officer.
            </p>
          </div>
          <div className="governance-role-card">
            <h3><span className="handbook-role-dot" style={{ background: "var(--warning)" }} /> Data Owner</h3>
            <p style={{ fontSize: 13 }}>
              Named on a Data Inventory entry. Only they (or an admin) may edit it, and only they
              can submit it for the Chief AI Governance Officer&rsquo;s approval.
            </p>
          </div>
          <div className="governance-role-card">
            <h3><span className="handbook-role-dot" style={{ background: "var(--danger)" }} /> Risk Owner</h3>
            <p style={{ fontSize: 13 }}>Accountable for treating and monitoring a specific risk once it&rsquo;s identified.</p>
          </div>
          <div className="governance-role-card">
            <h3><span className="handbook-role-dot" style={{ background: "var(--neutral-text)" }} /> Implementation Team</h3>
            <p style={{ fontSize: 13 }}>
              Engineers, data scientists, DevOps &mdash; write the documentation, perform the
              impact and risk assessments, and implement controls.
            </p>
          </div>
        </div>

        <div className="handbook-callout rule">
          <div className="handbook-callout-icon">⚖</div>
          <div>
            <div className="handbook-callout-title">Segregation of duties is enforced, not just asked for</div>
            <p>
              Whoever submits something for approval cannot be the one who approves it &mdash;
              not even an admin. The platform checks the audit trail for who submitted last, every
              time. If you submitted it, hand it to someone else.
            </p>
          </div>
        </div>
      </section>

      <section id="lifecycle">
        <h2>The AI system life cycle</h2>
        <p>
          Every AI system in the inventory moves through the same seven stages, in the same
          order, based on ISO/IEC 5338. You can&rsquo;t skip a stage or jump ahead &mdash; each
          one has a <strong>gate</strong>: a short list of things that have to be true before{" "}
          <strong>Advance stage</strong> is allowed. Nothing on a gate is a checkbox someone
          ticks; every item is computed live from the actual record, so it can&rsquo;t pass while
          the thing behind it is missing, and it re-opens on its own if that thing is later
          removed.
        </p>

        <StageDiagram />

        <p style={{ marginBottom: 22 }}>
          If a stage turns out to be premature &mdash; a release that isn&rsquo;t ready &mdash;{" "}
          <strong>Revert stage</strong> steps a system back one stage with a reason on record.
          Stepping back out of Deployment clears any standing release approval too; a re-release
          has to be approved again.
        </p>

        <GateReference
          stage="Inception"
          ordinal="Stage 1 of 7"
          intro="The system is registered and its exposure is understood before any design work starts."
          requirements={[
            { label: "AI System Owner assigned", detail: "They'll approve this system's impact and risk assessments." },
            { label: "Impact assessment completed", detail: "Who and what this system affects, scored across all eight ISO/IEC 42005 factors." },
            { label: "Risk assessment performed", detail: "At least one risk item recorded." },
          ]}
        />
        <GateReference
          stage="Design"
          ordinal="Stage 2 of 7"
          intro="One requirement, from the Design stage's own upload control."
          requirements={[{ label: "Design document uploaded", detail: "" }]}
        />
        <GateReference
          stage="Development"
          ordinal="Stage 3 of 7"
          intro="The system is built out — and what it's built on is on record."
          requirements={[
            { label: "Inventory details complete", detail: "Every A.4 field — purpose, resources, tooling, compute, hosting, team, oversight — filled in." },
            { label: "Approved dataset(s) recorded", detail: "At least one Data Inventory entry linked to this system, and that entry has cleared its own review — a draft link doesn't count." },
          ]}
        />
        <GateReference
          stage="Verification & Validation"
          ordinal="Stage 4 of 7"
          intro="The system is tested, and someone other than whoever built it signs off on releasing it."
          requirements={[
            { label: "Validation report uploaded", detail: "" },
            { label: "Release approved", detail: "Requested by one person, approved by the Chief AI Governance Officer — never the same person." },
            { label: "No untreated high risks", detail: "Every open risk item scoring in the High band (against the org's current risk criteria) has to be treated first." },
          ]}
        />
        <GateReference
          stage="Deployment"
          ordinal="Stage 5 of 7"
          intro="Live in production — with someone watching it and a plan if it misbehaves."
          requirements={[
            { label: "Monitoring plan uploaded", detail: "" },
            { label: "Monitoring owner assigned", detail: "" },
            { label: "Impact & risk assessments current", detail: "Neither is overdue for its yearly review." },
            { label: "Incident escalation path recorded", detail: "Who gets contacted, and how, when this system misbehaves." },
          ]}
        />
        <GateReference
          stage="Operation & Monitoring"
          ordinal="Stage 6 of 7"
          intro="The system runs. Moving on from here means starting retirement — a decision, not a drift."
          requirements={[
            { label: "Retirement reason recorded", detail: "Say why this system is being retired before starting the process." },
            { label: "Retirement approved", detail: "Requested by one person, approved by the Chief AI Governance Officer." },
          ]}
        />
        <GateReference
          stage="Retirement"
          ordinal="Stage 7 of 7"
          intro="The last stage. Archive replaces Advance stage here — it's the step that actually takes the system off the active roster."
          requirements={[
            { label: "Retirement sign-off document uploaded", detail: "" },
            { label: "Retention period set", detail: "How long this system's full record — assessments, evidence, audit trail — must be kept before it can ever be deleted." },
          ]}
        />
      </section>

      <section id="data-inventory">
        <h2>The Data Inventory</h2>
        <p>
          Every dataset an AI system draws on gets its own entry &mdash; its own owner, its own
          review, independent of any one system that happens to use it. A dataset can outlive the
          system it was built for.
        </p>

        <ol className="handbook-workflow">
          <li>
            <h4>A Data Owner fills in the entry</h4>
            <p>
              <span className="actor">Data Owner</span> &mdash; name, type, source, whether
              personal data is involved, classification, retention period, and the ISO 42001 A.7
              fields (acquisition, quality measures, provenance, preparation). Link it to the AI
              system(s) that use it.
            </p>
          </li>
          <li>
            <h4>Submit for approval</h4>
            <p>
              <span className="actor">Data Owner</span> &mdash; needs a name and an assigned owner
              first. Status moves to <span className="status-badge" data-status="in_review">Pending approval</span>.
            </p>
          </li>
          <li>
            <h4>Chief AI Governance Officer approves</h4>
            <p>
              <span className="actor">Chief AI Governance Officer</span> &mdash; someone other
              than whoever submitted it. Status moves to{" "}
              <span className="status-badge" data-status="approved">Approved</span>, and this is
              what an AI system&rsquo;s Development-stage gate is actually checking for.
            </p>
          </li>
        </ol>

        <div className="handbook-callout rule">
          <div className="handbook-callout-icon">↺</div>
          <div>
            <div className="handbook-callout-title">Any edit sends it back to draft</div>
            <p>
              An approval describes the dataset exactly as it stood when it was signed off. Change
              so much as one field afterward &mdash; even on an already-approved entry &mdash; and
              it reverts to <span className="status-badge" data-status="draft">Draft</span>{" "}
              automatically, with the approval cleared. It has to be re-submitted and
              re-approved. This is deliberate: an approval that survived a silent edit would mean
              nothing.
            </p>
          </div>
        </div>

        <p>
          Only the named Data Owner (or an admin) can edit or delete an entry. Deleting the AI
          system it&rsquo;s linked to doesn&rsquo;t delete the dataset &mdash; the link is simply
          cleared, and the dataset&rsquo;s approval stands untouched, since the data itself
          hasn&rsquo;t changed.
        </p>
      </section>

      <section id="assessments">
        <h2>Impact &amp; risk assessments</h2>
        <p>
          Every AI system gets exactly one impact assessment and, once that&rsquo;s complete, one
          risk assessment &mdash; both re-visited and re-approved over the system&rsquo;s life,
          rather than piling up a new copy each time.
        </p>

        <h3 style={{ marginTop: 24 }}>The impact assessment comes first</h3>
        <p>
          Structured per ISO/IEC 42005: a fixed scorecard of eight factors &mdash; benefits,
          harms, and the criteria behind each, with a 1&ndash;5 score. A risk assessment
          can&rsquo;t even be started until this one reads{" "}
          <span className="status-badge" data-status="completed">Completed</span>.
        </p>

        <h3 style={{ marginTop: 24 }}>Then the risk assessment</h3>
        <p>
          Risk items live in a spreadsheet-style grid: category, description, likelihood, impact.{" "}
          <strong>Inherent risk score</strong> (likelihood × impact) computes itself as you type
          &mdash; never enter it by hand. Treating a risk records a mitigation and a residual
          likelihood/impact, giving a <strong>residual risk score</strong> the same way.
        </p>

        <div className="handbook-matrix-legend" aria-hidden="true">
          <div className="handbook-matrix-legend-item"><span className="handbook-matrix-swatch low" />Low</div>
          <div className="handbook-matrix-legend-item"><span className="handbook-matrix-swatch med" />Medium</div>
          <div className="handbook-matrix-legend-item"><span className="handbook-matrix-swatch high" />High</div>
        </div>
        <p style={{ fontSize: 13 }}>
          The Low / Medium / High bands come from <strong>Risk criteria</strong> (an admin sets
          the org&rsquo;s risk appetite once, from the risk portfolio view; every score everywhere
          reads against whatever is currently set). A risk item scoring High and still open blocks
          its AI system at the Verification &amp; Validation gate until it&rsquo;s treated.
        </p>

        <h3 style={{ marginTop: 24 }}>Both assessments approve the same way</h3>
        <ol className="handbook-workflow">
          <li>
            <h4>Submit for owner approval</h4>
            <p>
              <span className="actor">Implementation Team</span> &mdash; moves to{" "}
              <span className="status-badge" data-status="in_review">Pending owner approval</span>.
              If the AI System Owner is the one submitting, this step is skipped entirely and it
              goes straight to step 3 &mdash; they can&rsquo;t meaningfully approve their own work.
            </p>
          </li>
          <li>
            <h4>AI System Owner approves</h4>
            <p>
              <span className="actor">AI System Owner</span> &mdash; moves to{" "}
              <span className="status-badge" data-status="in_review">Pending CAIGO approval</span>.
            </p>
          </li>
          <li>
            <h4>Chief AI Governance Officer approves</h4>
            <p>
              <span className="actor">Chief AI Governance Officer</span> &mdash; moves to{" "}
              <span className="status-badge" data-status="completed">Completed</span>, and stamps
              the next yearly review date.
            </p>
          </li>
        </ol>

        <div className="handbook-callout rule">
          <div className="handbook-callout-icon">↺</div>
          <div>
            <div className="handbook-callout-title">Same withdrawal rule as the Data Inventory</div>
            <p>
              Changing what was assessed &mdash; scores, mitigation, owner, deadline &mdash; sends
              a Completed assessment back to draft. <strong>Treating a risk item is different</strong>:
              closing it out (with evidence attached) is progress <em>against</em> an approved
              assessment, not a change to what was assessed, so it doesn&rsquo;t disturb a
              standing approval.
            </p>
          </div>
        </div>
      </section>

      <section id="policies">
        <h2>Policies &amp; procedures</h2>
        <p>
          Governance documents follow their own, simpler chain &mdash; draft, review, approved,
          retired &mdash; with the same segregation-of-duties rule as everything else.
        </p>

        <dl className="handbook-deflist">
          <div>
            <dt><span className="status-badge" data-status="draft">Draft</span></dt>
            <dd>Freely editable. This is the only status a document can be deleted from.</dd>
          </div>
          <div>
            <dt><span className="status-badge" data-status="in_review">In review</span></dt>
            <dd>Submitted, waiting on the Chief AI Governance Officer. Locked from further edits.</dd>
          </div>
          <div>
            <dt><span className="status-badge" data-status="approved">Approved</span></dt>
            <dd>In force. A procedure can name the policy it implements; a policy can&rsquo;t retire while a live procedure still implements it.</dd>
          </div>
          <div>
            <dt><span className="status-badge" data-status="retired">Retired</span></dt>
            <dd>Superseded, kept permanently for the record &mdash; not deleted, so what governed the organization (and when) stays intact.</dd>
          </div>
        </dl>

        <p>
          Each carries its own document library &mdash; supporting evidence, filed in folders if
          you like &mdash; and a version number that bumps every time a draft&rsquo;s file set
          changes.
        </p>
      </section>

      <section id="archive">
        <h2>Retiring a system</h2>
        <p>
          Retirement is the seventh stage; <strong>archiving</strong> is the step that actually
          closes it out and removes the system from the active inventory.
        </p>

        <article>
          <h3 style={{ marginBottom: 10 }}>What archiving means</h3>
          <p style={{ marginBottom: 10 }}>
            The system disappears from the active inventory grid and every coverage count on the
            dashboard &mdash; it&rsquo;s a retired record, not part of the active estate. Its full
            history &mdash; assessments, evidence, audit trail &mdash; stays completely readable,
            forever, under <strong>Archive</strong> in the sidebar.
          </p>
          <p style={{ marginBottom: 0 }}>
            It stays <strong>frozen</strong>: nothing about it &mdash; its stage, its retention
            date, its owner, its documents &mdash; can be changed by anyone, through any path,
            once it&rsquo;s archived. The only thing that can ever happen to it next is deletion,
            and only once its retention date has actually passed.
          </p>
        </article>

        <div className="handbook-callout danger">
          <div className="handbook-callout-icon">🔒</div>
          <div>
            <div className="handbook-callout-title">Retention is the whole point of the archive</div>
            <p>
              The date set on the Retirement stage is a real commitment. Nobody &mdash; not an
              admin, not by any route &mdash; can shorten it, extend it, or touch anything else
              about an archived record. If a system needs deleting, that request goes to its
              retention date, and stops there until it passes.
            </p>
          </div>
        </div>
      </section>

      <section id="evidence">
        <h2>Evidence &amp; documents</h2>
        <p>
          Most records &mdash; AI systems, impact assessments, risk items, policies, procedures
          &mdash; carry their own document library: upload, organize into folders, tag to a
          framework control. PDF, Word, Excel, CSV, images, and plain text are accepted, up to
          25MB a file.
        </p>

        <h3 style={{ marginTop: 22 }}>Stage-gate uploads are typed</h3>
        <p>
          The four documents a life cycle gate looks for &mdash; Design document, Validation
          report, Monitoring plan, Retirement sign-off &mdash; are uploaded from that
          stage&rsquo;s own control, which tags the file correctly on its own. A file dropped in
          through the general document browser instead won&rsquo;t satisfy a gate; it isn&rsquo;t
          tagged the same way.
        </p>

        <h3 style={{ marginTop: 22 }}>Evidence is load-bearing for a closed risk</h3>
        <p>
          A risk item can&rsquo;t be marked closed without at least one document attached as proof
          of the mitigation. Delete that last piece of proof afterward, and the item reopens
          automatically &mdash; a closed item can&rsquo;t outlive what proved it was handled.
        </p>
      </section>

      <section id="frameworks">
        <h2>Frameworks &amp; the Statement of Applicability</h2>
        <p>
          Under <strong>Frameworks</strong>, every clause of ISO/IEC 42001 and every Annex A
          control is listed with the evidence tagged against it &mdash; policies, procedures,
          evidence documents, and both assessment types can all be tagged to a control from
          wherever you&rsquo;re viewing them.
        </p>
        <p>
          The <strong>Statement of Applicability</strong> records, per Annex A control, whether it
          applies to the organization &mdash; and if not, why. Marking a control Not Applicable
          requires a justification; there&rsquo;s no silent way to exclude one.
        </p>
      </section>

      <section id="management-system">
        <h2>The rest of the management system</h2>
        <p>
          Beyond the AI systems themselves, ISO/IEC 42001 asks for the machinery that runs
          them. Each of these is an ordinary record that anyone who can edit may create, and
          each one&rsquo;s standing &mdash; overdue, due soon, open &mdash; is worked out from its
          own dates, never ticked by hand. Overdue items reach the dashboard.
        </p>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Area</th><th>What it holds</th><th>ISO/IEC 42001</th></tr></thead>
            <tbody>
              <tr><td><a href="/organization-context">Organization context</a></td><td>One record for the whole organization: what it does, how it uses AI, and who has an interest in it. The assistant can draft it for review.</td><td>4</td></tr>
              <tr><td><a href="/objectives">AI Objectives</a></td><td>What you want your use of AI to achieve, measured over time. Whether an objective is on track, off track or achieved is computed from its measurements and target date.</td><td>6.2, 9.1</td></tr>
              <tr><td><a href="/changes">Changes</a></td><td>Planned changes to the AI management system, with a target date.</td><td>6.3</td></tr>
              <tr><td><a href="/competence">Competence</a></td><td>What people need to know to carry out their AI roles, and a record of who has it.</td><td>7.2, 7.3</td></tr>
              <tr><td><a href="/communications">Communication</a></td><td>What the organization says about its AI management system, to whom and when. The next due date is computed.</td><td>7.4</td></tr>
              <tr><td><a href="/audit-programs">Internal audits</a></td><td>A program of audits on a schedule you set, with findings.</td><td>9.2</td></tr>
              <tr><td><a href="/management-review">Management review</a></td><td>Leadership&rsquo;s periodic review of the system: its settings and its meetings.</td><td>9.3</td></tr>
              <tr><td><a href="/corrective-actions">Corrective actions</a></td><td>Nonconformities and what was done about them.</td><td>10.2</td></tr>
              <tr><td><a href="/improvements">Improvements</a></td><td>Opportunities to improve, tracked to completion.</td><td>10.1</td></tr>
              <tr><td><a href="/incidents">Incidents</a></td><td>Anything that went wrong with an AI system. For a serious incident the EU AI Act sets reporting deadlines (Article 73), which the record counts down.</td><td>A.8.4</td></tr>
              <tr><td><a href="/suppliers">Suppliers</a></td><td>The third parties behind your AI systems: reviews, contract dates, and which systems depend on them.</td><td>A.10.2&ndash;A.10.4</td></tr>
              <tr><td><a href="/concerns">Concerns</a></td><td>Staff raise a concern from their staff home and can follow it with a tracking code. Only administrators can read concerns, and each has to be acknowledged within the number of days set in the concerns settings.</td><td>A.3.3</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section id="ai-use">
        <h2>Governing staff use of AI</h2>
        <p>
          The platform also governs how people use AI day to day, in four parts that work
          together. It is the practical side of ISO/IEC 42001 A.9.2 (use of AI systems).
        </p>

        <dl className="handbook-deflist">
          <div><dt>The register</dt><dd><a href="/ai-tools">AI Tools</a> lists the third-party tools staff might use. Each is approved, restricted, revoked or still only catalogued, with the <strong>most sensitive data it may be given</strong> (public, internal or confidential), the conditions of use, and a review date. A tool that isn&rsquo;t approved is treated as unapproved.</dd></div>
          <div><dt>Requests</dt><dd>An employee asks for a tool from their staff home and says why. The Chief AI Governance Officer approves or says no, and a refusal needs a note to the employee. Nobody decides their own request.</dd></div>
          <div><dt>Data rules</dt><dd><a href="/ai-tools/rules">Data rules</a> say what must not be pasted or typed into AI tools: card numbers, keys, personal identifiers, your own keywords or patterns. Each is set to <em>monitor</em> (count it), <em>warn</em> (the person confirms or cancels) or <em>block</em>; new rules start on block. A rule only applies to data more sensitive than the tool is cleared for, so a tool approved for confidential data is not stopped by a rule about internal data. The rule tester shows what a rule would catch.</dd></div>
          <div><dt>The browser extension</dt><dd>Installed by IT on Chrome and Edge, it carries the policy out: an unapproved site shows a page that offers <strong>Request this tool</strong> (blocked by default, or warn or monitor if you choose), and the data rules are checked in the browser before anything is sent. Only counts leave the browser &mdash; never what was typed, never a page address.</dd></div>
        </dl>

        <div className="handbook-callout rule">
          <div className="handbook-callout-icon">🔒</div>
          <div>
            <div className="handbook-callout-title">What is and isn&rsquo;t seen</div>
            <p>
              <a href="/ai-tools/usage">Usage</a> shows counts: visits to unapproved sites,
              sites blocked, and sensitive data stopped, per site and per rule. There is no text
              and no page address behind them. The extension covers only the browsers it is
              installed in; desktop apps, other browsers and mobile are outside it. In{" "}
              <a href="/ai-tools/settings">Settings</a> you choose what happens at an unapproved
              site, write the notice staff read, and create or replace the key the extension uses.
            </p>
          </div>
        </div>
      </section>

      <section id="assistant">
        <h2>The assistant</h2>
        <p>
          The assistant panel answers questions from your own records and documents, and the
          &ldquo;Draft with AI&rdquo; buttons write a first version of a record for you to
          review. It needs an AI provider and key, set in <a href="/settings">Settings</a>;
          without one, everything else works as normal.
        </p>
        <dl className="handbook-deflist">
          <div><dt>It cites its sources</dt><dd>Every answer points to the passages it came from, and a citation to something it was never given is removed before you see the answer.</dd></div>
          <div><dt>It can say &ldquo;the record doesn&rsquo;t cover that&rdquo;</dt><dd>If nothing relevant is found, it says so rather than guessing. A document that couldn&rsquo;t be read is flagged, so &ldquo;not found&rdquo; is never confused with &ldquo;couldn&rsquo;t look&rdquo;.</dd></div>
          <div><dt>Exact counts</dt><dd>For questions like &ldquo;how many AI systems have no impact assessment&rdquo; it counts the same way the dashboard does, so the two never disagree.</dd></div>
          <div><dt>It never changes anything</dt><dd>It can read and propose; it cannot save, submit, approve or delete. A draft waits for you to accept it, and accepting it goes through the normal permissions and is recorded like any other edit.</dd></div>
        </dl>
        <p>
          Text in a document is treated as data, not as instructions, so a document that tells a
          model to ignore its rules is read as the content it is.
        </p>
      </section>

      <section id="dashboard">
        <h2>Reading the dashboard</h2>
        <p>
          Coverage rings and portfolio charts summarize the whole estate at a glance; the{" "}
          <strong>Needs attention</strong> panel is the actionable part &mdash; every item links
          straight to the record behind it.
        </p>

        <dl className="handbook-deflist">
          <div><dt><span className="handbook-attn-dot danger" />Overdue treatments</dt><dd>Open risk items past their treatment deadline.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />No impact assessment</dt><dd>AI systems with nothing on file yet.</dd></div>
          <div><dt><span className="handbook-attn-dot warning" />Assessments review overdue</dt><dd>Past their yearly re-review date.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />Retention expired</dt><dd>Archived systems now eligible for deletion.</dd></div>
          <div><dt><span className="handbook-attn-dot warning" />Unassessed AI systems</dt><dd>No risk assessment started.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />High-risk assessments</dt><dd>Carrying an open item in the High band.</dd></div>
          <div><dt><span className="handbook-attn-dot warning" />Awaiting review</dt><dd>Sitting in someone's approval queue.</dd></div>
          <div><dt><span className="handbook-attn-dot warning" />Vacant governance roles</dt><dd>A role with zero holders.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />AI systems without an owner</dt><dd>Blocks the Inception gate.</dd></div>
          <div><dt><span className="handbook-attn-dot warning" />Owner isn't a real account</dt><dd>A Risk or Data Owner field that doesn't resolve to an actual user.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />Corrective actions overdue</dt><dd>Nonconformities past their due date.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />Concerns not yet acknowledged</dt><dd>Raised by staff and waiting longer than the concerns settings allow.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />Supplier reviews overdue</dt><dd>Past the date each supplier is next due a review.</dd></div>
          <div><dt><span className="handbook-attn-dot warning" />Requests for AI tools awaiting a decision</dt><dd>Employees waiting for the Chief AI Governance Officer.</dd></div>
          <div><dt><span className="handbook-attn-dot warning" />Visits to unapproved AI sites; sensitive data stopped</dt><dd>The last seven days of counts from the browser extension.</dd></div>
          <div><dt><span className="handbook-attn-dot danger" />Framework controls with no coverage</dt><dd>Nothing is tagged to them yet; &ldquo;tagged but no longer current&rdquo; counts the ones whose records have gone stale.</dd></div>
        </dl>
        <p>
          That is a selection: the panel groups everything that needs attention by area &mdash;
          incidents and corrective actions, risk and assessments, AI systems, data and suppliers,
          objectives, management-system planning and framework coverage &mdash; and each count
          links to the records behind it.
        </p>

        <p id="delegate" style={{ marginTop: 20 }}>
          <strong>When the Chief AI Governance Officer is away:</strong> from Roles &amp;
          Responsibilities, they (or an admin) can name a time-boxed delegate. The delegate can
          approve everything CAIGO-gated for the window set, and shows up everywhere with the same
          badge &mdash; nothing else needs to change.
        </p>
      </section>

      <section id="account">
        <h2>Your account &amp; signing in</h2>
        <p>
          Everyone manages their own sign-in from <a href="/account">Your account</a> (in the
          sidebar).
        </p>
        <dl className="handbook-deflist">
          <div><dt>Passwords</dt><dd>At least 12 characters. A password is refused if it is a common word, even a disguised one (<code>P@ssw0rd2024!</code>), a keyboard or number run, almost all one character, or built from your own name or email. Your last five can&rsquo;t be reused. A few unrelated words works well.</dd></div>
          <div><dt>A temporary password</dt><dd>If an admin created your account, or reset your password, the one you were given is temporary: you can do nothing else until you choose your own.</dd></div>
          <div><dt>Two-step sign-in</dt><dd>Turn it on with an authenticator app (Google or Microsoft Authenticator, Authy, 1Password): scan the code, enter one code to prove it works, then save your <strong>ten recovery codes</strong>. They are shown once, each works once, and they are for when your phone isn&rsquo;t to hand. After that, signing in needs your password and a code.</dd></div>
          <div><dt>Turning it off, or new recovery codes</dt><dd>Both need your password and a current code, so someone at an unlocked laptop can&rsquo;t do either.</dd></div>
          <div><dt>Other devices</dt><dd><em>Sign out of other devices</em> ends every session except this one. Changing your password does the same.</dd></div>
          <div><dt>Too many wrong attempts</dt><dd>Five wrong passwords lock the account for 15 minutes, and five wrong codes lock the codes for 15 minutes.</dd></div>
        </dl>

        <h3 style={{ marginTop: 22 }}>For administrators</h3>
        <ul>
          <li><strong>Reset password</strong> (in <a href="/users">Users</a>) gives a person a one-time password, shown to you once, and signs them out everywhere.</li>
          <li><strong>Reset two-step</strong> is for someone who has lost both their phone and their recovery codes. It signs them out everywhere, and you can&rsquo;t do it for yourself &mdash; ask another administrator.</li>
          <li><strong>Sign-in security</strong> (also in Users) can <em>require two-step sign-in for administrators</em>. It starts off. You can only switch it on once you have two-step sign-in yourself, and from then on an administrator without it can do nothing but set it up.</li>
          <li>Sign-ins, failed attempts, lockouts and password or two-step changes are all recorded against the account in the audit log.</li>
        </ul>
      </section>

      <section id="bulk">
        <h2>Editing in bulk, safely</h2>
        <p>
          Every grid &mdash; the AI System Inventory, the Data Inventory, a Risk
          Assessment&rsquo;s items &mdash; can be exported to a spreadsheet, edited offline, and
          re-uploaded.
        </p>

        <div className="handbook-callout rule">
          <div className="handbook-callout-icon">🆔</div>
          <div>
            <div className="handbook-callout-title">Always re-upload the file you exported</div>
            <p>
              Every export carries a leading <code>ID</code> column. Editing a row in that file
              and re-uploading it updates that exact record in place &mdash; its assessments, its
              review, its documents all stay correctly attached. A row you delete from the file is
              simply <strong>left alone</strong>, not removed from the platform; nothing is ever
              deleted by an upload. A brand-new row with no <code>ID</code> becomes a new record.
            </p>
          </div>
        </div>

        <p>
          Building the file by hand instead? Leave the <code>ID</code> column out (or blank) and
          every row becomes a new record &mdash; never delete something by leaving it out of a
          hand-built file. To actually remove a record, use its delete action; that&rsquo;s the
          one path that runs every check a bulk upload can&rsquo;t &mdash; like an archived
          system&rsquo;s retention.
        </p>
      </section>

      <section id="reference">
        <h2>Quick reference</h2>

        <h3>What each account role can do</h3>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Action</th><th>Viewer</th><th>Contributor</th><th>Admin</th></tr></thead>
            <tbody>
              <tr><td>View everything</td><td>Yes</td><td>Yes</td><td>Yes</td></tr>
              <tr><td>Create &amp; edit records</td><td>&mdash;</td><td>Yes</td><td>Yes</td></tr>
              <tr><td>Approve (as CAIGO, if assigned)</td><td>&mdash;</td><td>&mdash;</td><td>Yes</td></tr>
              <tr><td>Manage user accounts</td><td>&mdash;</td><td>&mdash;</td><td>Yes</td></tr>
              <tr><td>Set organization risk criteria</td><td>&mdash;</td><td>&mdash;</td><td>Yes</td></tr>
              <tr><td>Decide AI tool requests (as CAIGO)</td><td>&mdash;</td><td>&mdash;</td><td>Yes</td></tr>
              <tr><td>AI use settings and the extension key</td><td>&mdash;</td><td>&mdash;</td><td>Yes</td></tr>
              <tr><td>Read and handle concerns</td><td>&mdash;</td><td>&mdash;</td><td>Yes</td></tr>
            </tbody>
          </table>
        </div>
        <p style={{ marginTop: 8 }}>
          The <strong>Employee</strong> login isn&rsquo;t in this table: it holds none of these
          actions and reaches only the staff home.
        </p>

        <h3 style={{ marginTop: 26 }}>Where to find things</h3>
        <div className="handbook-pagemap">
          <div className="handbook-pagemap-item"><a href="/">Dashboard</a><span>Coverage &amp; attention</span></div>
          <div className="handbook-pagemap-item"><a href="/ai-systems">AI System Inventory</a><span>Register &amp; life cycle</span></div>
          <div className="handbook-pagemap-item"><a href="/data-inventory">Data Inventory</a><span>Datasets &amp; review</span></div>
          <div className="handbook-pagemap-item"><a href="/archive">Archive</a><span>Retired systems</span></div>
          <div className="handbook-pagemap-item"><a href="/risk-assessments">Impact &amp; Risk Assessments</a><span>Every assessment</span></div>
          <div className="handbook-pagemap-item"><a href="/policies">Policies</a><span /></div>
          <div className="handbook-pagemap-item"><a href="/procedures">Procedures</a><span /></div>
          <div className="handbook-pagemap-item"><a href="/frameworks">Frameworks</a><span>Clauses, controls &amp; the SoA</span></div>
          <div className="handbook-pagemap-item"><a href="/organization-context">Organization Context</a><span>Clause 4</span></div>
          <div className="handbook-pagemap-item"><a href="/ai-tools">AI Tools</a><span>Register, requests, rules, usage</span></div>
          <div className="handbook-pagemap-item"><a href="/suppliers">Suppliers</a><span>Third parties</span></div>
          <div className="handbook-pagemap-item"><a href="/objectives">AI Objectives</a><span>Targets &amp; measurements</span></div>
          <div className="handbook-pagemap-item"><a href="/audit-programs">Internal Audits</a><span>Programs &amp; findings</span></div>
          <div className="handbook-pagemap-item"><a href="/management-review">Management Review</a><span>Meetings</span></div>
          <div className="handbook-pagemap-item"><a href="/corrective-actions">Corrective Actions</a><span>Nonconformities</span></div>
          <div className="handbook-pagemap-item"><a href="/incidents">Incidents</a><span>Including Article 73 deadlines</span></div>
          <div className="handbook-pagemap-item"><a href="/concerns">Concerns</a><span>Raised by staff</span></div>
          <div className="handbook-pagemap-item"><a href="/governance">Roles &amp; Responsibilities</a><span>Governance roles &amp; delegation</span></div>
          <div className="handbook-pagemap-item"><a href="/users">Users</a><span>Accounts and sign-in security (admin)</span></div>
          <div className="handbook-pagemap-item"><a href="/account">Your account</a><span>Password &amp; two-step sign-in</span></div>
          <div className="handbook-pagemap-item"><a href="/settings">Settings</a><span>AI provider &amp; assistant</span></div>
        </div>
      </section>
    </section>
  );
}
