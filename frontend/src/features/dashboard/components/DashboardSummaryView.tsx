import { Link } from "react-router-dom";

import { ProgressRing } from "../../../shared/components/ProgressRing";
import { SegmentedBar, type Segment } from "../../../shared/components/SegmentedBar";
import { StatCard } from "../../../shared/components/StatCard";
import { RiskMatrix } from "../../risk-assessments/components/RiskMatrix";
import { useDashboardSummary } from "../hooks";
import type { AttentionItem, MyRiskItem, StatusCounts } from "../types";

const ATTENTION_LINKS: Record<string, string> = {
  overdue_treatments: "/risk-assessments",
  unassessed_ai_systems: "/ai-systems",
  high_risk_assessments: "/risk-assessments",
  awaiting_review: "/policies",
};

const STATUS_TONES: Record<string, Segment["tone"]> = {
  approved: "success",
  completed: "success",
  in_review: "warning",
  in_progress: "warning",
  retired: "neutral",
  draft: "neutral",
};

function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

function statusSegments(counts: Record<string, number>): Segment[] {
  return Object.entries(counts).map(([key, value]) => ({
    key,
    label: humanize(key),
    value,
    tone: STATUS_TONES[key] ?? "primary",
  }));
}

function CountCard({ label, counts, to }: { label: string; counts: StatusCounts; to: string }) {
  return (
    <StatCard label={label} value={<Link to={to}>{counts.total}</Link>}>
      <SegmentedBar segments={statusSegments(counts.by_status)} emptyLabel="None yet." />
    </StatCard>
  );
}

function AttentionPanel({ items }: { items: AttentionItem[] }) {
  if (items.length === 0) {
    return (
      <div className="attention-panel is-clear">
        <div className="attention-clear-mark" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6 9 17l-5-5" />
          </svg>
        </div>
        <div>
          <h2>Nothing needs attention</h2>
          <p>No overdue treatments, unassessed systems, or items awaiting review.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="attention-panel">
      <h2>Needs Attention</h2>
      <ul>
        {items.map((item) => (
          <li key={item.key} data-severity={item.severity}>
            <span className="attention-count">{item.count}</span>
            <Link to={ATTENTION_LINKS[item.key] ?? "/"}>{item.label}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MyRiskItemsPanel({ items }: { items: MyRiskItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="dashboard-card">
      <h3>My Risk Items</h3>
      <p>Risk items you own that are still open.</p>
      <ul className="my-risk-items-list">
        {items.map((item) => (
          <li key={item.row_id} data-overdue={item.overdue}>
            <Link to={`/risk-assessments/${item.risk_assessment_id}`}>
              {item.category ?? "Risk item"}
            </Link>
            {item.description && <span className="my-risk-item-desc">{item.description}</span>}
            <span className="my-risk-item-meta">
              {item.overdue && <span className="flag-chip">Overdue</span>}
              {item.treatment_deadline && <span>Due {item.treatment_deadline}</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DashboardSummaryView() {
  const { data: summary, isLoading, isError } = useDashboardSummary();

  if (isLoading) return <p>Loading dashboard...</p>;
  if (isError || !summary) return <p>Failed to load dashboard.</p>;

  const { risk_items: riskItems, coverage, criteria } = summary;
  const reduction =
    riskItems.average_inherent_score && riskItems.average_residual_score !== null
      ? Math.round(
          ((riskItems.average_inherent_score - riskItems.average_residual_score) /
            riskItems.average_inherent_score) *
            100,
        )
      : null;

  const severitySegments: Segment[] = [
    { key: "high", label: "High", value: riskItems.by_severity.high ?? 0, tone: "high" },
    { key: "medium", label: "Medium", value: riskItems.by_severity.medium ?? 0, tone: "medium" },
    { key: "low", label: "Low", value: riskItems.by_severity.low ?? 0, tone: "low" },
  ];

  const tierSegments: Segment[] = Object.entries(summary.ai_systems.by_risk_tier).map(
    ([key, value]) => ({
      key,
      label: humanize(key),
      value,
      tone: key === "high" ? "high" : key === "limited" ? "medium" : "low",
    }),
  );

  return (
    <div className="dashboard">
      <AttentionPanel items={summary.attention} />

      <MyRiskItemsPanel items={summary.my_risk_items} />

      <section className="dashboard-section">
        <h2>Risk Posture</h2>
        <div className="dashboard-grid">
          <StatCard
            label="Risk items"
            value={riskItems.total}
            hint={`${riskItems.untreated_count} still open`}
          >
            <SegmentedBar segments={severitySegments} emptyLabel="No risk items yet." />
          </StatCard>

          <StatCard
            label="Overdue treatments"
            value={riskItems.overdue_count}
            tone={riskItems.overdue_count > 0 ? "danger" : "success"}
            hint={
              riskItems.overdue_count > 0
                ? "Past their treatment deadline"
                : "All treatments on schedule"
            }
          />

          <StatCard
            label="Average risk score"
            value={riskItems.average_inherent_score ?? "—"}
            hint={
              reduction !== null
                ? `${reduction}% lower after mitigation (${riskItems.average_residual_score} residual)`
                : "No residual scores recorded yet"
            }
          />

          <StatCard
            label="High-risk assessments"
            value={summary.risk_assessments.high_risk_count}
            tone={summary.risk_assessments.high_risk_count > 0 ? "warning" : "default"}
            hint={`Rated ${criteria.high_min_score} or above`}
          />

          <StatCard
            label="Reviews overdue"
            value={coverage.assessments_review_overdue}
            tone={coverage.assessments_review_overdue > 0 ? "danger" : "default"}
            hint="Impact and risk assessments are reviewed yearly"
          />
        </div>
      </section>

      <section className="dashboard-section">
        <h2>Coverage</h2>
        <div className="dashboard-split">
          <div className="dashboard-card ring-row">
            <ProgressRing
              value={coverage.ai_systems_impact_assessed}
              total={coverage.ai_systems_total}
              label="Impact assessed"
            />
            <ProgressRing
              value={coverage.ai_systems_assessed}
              total={coverage.ai_systems_total}
              label="Risk assessed"
            />
            <ProgressRing
              value={coverage.policies_approved}
              total={coverage.policies_total}
              label="Policies approved"
            />
            <ProgressRing
              value={coverage.procedures_approved}
              total={coverage.procedures_total}
              label="Procedures approved"
            />
          </div>

          <div className="dashboard-card">
            <h3>Portfolio Risk Matrix</h3>
            <RiskMatrix
              cells={summary.matrix}
              bands={criteria}
              caption="All risk items across every assessment"
            />
          </div>
        </div>
      </section>

      <section className="dashboard-section">
        <h2>Inventory</h2>
        <div className="dashboard-grid">
          <CountCard label="Policies" counts={summary.policies} to="/policies" />
          <CountCard label="Procedures" counts={summary.procedures} to="/procedures" />
          <StatCard
            label="AI Systems"
            value={<Link to="/ai-systems">{summary.ai_systems.total}</Link>}
          >
            <SegmentedBar segments={tierSegments} emptyLabel="None yet." />
          </StatCard>
          <CountCard
            label="Risk Assessments"
            counts={summary.risk_assessments}
            to="/risk-assessments"
          />
        </div>
      </section>
    </div>
  );
}
