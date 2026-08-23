import { useDashboardSummary } from "../hooks";

function BreakdownList({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts);
  if (entries.length === 0) return <p>None yet.</p>;

  return (
    <ul>
      {entries.map(([key, count]) => (
        <li key={key}>
          {key.replace(/_/g, " ")}: {count}
        </li>
      ))}
    </ul>
  );
}

export function DashboardSummaryView() {
  const { data: summary, isLoading, isError } = useDashboardSummary();

  if (isLoading) return <p>Loading dashboard...</p>;
  if (isError || !summary) return <p>Failed to load dashboard.</p>;

  return (
    <div className="dashboard-summary">
      <section>
        <h2>Policies</h2>
        <p>Total: {summary.policies.total}</p>
        <BreakdownList counts={summary.policies.by_status} />
      </section>

      <section>
        <h2>Procedures</h2>
        <p>Total: {summary.procedures.total}</p>
        <BreakdownList counts={summary.procedures.by_status} />
      </section>

      <section>
        <h2>AI System Inventory</h2>
        <p>Total: {summary.ai_systems.total}</p>
        <BreakdownList counts={summary.ai_systems.by_risk_tier} />
      </section>

      <section>
        <h2>Risk Assessments</h2>
        <p>Total: {summary.risk_assessments.total}</p>
        <p>High Risk: {summary.risk_assessments.high_risk_count}</p>
        <BreakdownList counts={summary.risk_assessments.by_status} />
      </section>
    </div>
  );
}
