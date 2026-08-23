import { ProgressRing } from "../../../shared/components/ProgressRing";
import { SegmentedBar, type Segment } from "../../../shared/components/SegmentedBar";
import { StatCard } from "../../../shared/components/StatCard";
import { useRiskPortfolioSummary } from "../hooks";
import { RiskMatrix } from "./RiskMatrix";

export function RiskPortfolioSummaryView() {
  const { data: summary, isLoading, isError } = useRiskPortfolioSummary();

  if (isLoading) return <p>Loading risk summary...</p>;
  if (isError || !summary) return <p>Failed to load risk summary.</p>;

  const { risk_items: riskItems, criteria } = summary;

  const severitySegments: Segment[] = [
    { key: "high", label: "High", value: riskItems.by_severity.high ?? 0, tone: "high" },
    { key: "medium", label: "Medium", value: riskItems.by_severity.medium ?? 0, tone: "medium" },
    { key: "low", label: "Low", value: riskItems.by_severity.low ?? 0, tone: "low" },
  ];

  const treated = riskItems.total - riskItems.untreated_count;

  return (
    <div className="portfolio-summary">
      <div className="dashboard-grid">
        <StatCard
          label="Risk items"
          value={riskItems.total}
          hint={`Across ${summary.total_assessments} assessment${
            summary.total_assessments === 1 ? "" : "s"
          }`}
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
          label="High-risk assessments"
          value={summary.high_risk_count}
          tone={summary.high_risk_count > 0 ? "warning" : "default"}
          hint={`Rated ${criteria.high_min_score} or above`}
        />

        <div className="stat-card">
          <ProgressRing
            value={treated}
            total={riskItems.total}
            label="Risks treated"
            caption={`${treated} of ${riskItems.total} closed out`}
          />
        </div>
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
  );
}
