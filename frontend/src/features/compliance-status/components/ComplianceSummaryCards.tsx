import { SegmentedBar, type Segment } from "../../../shared/components/SegmentedBar";
import { StatCard } from "../../../shared/components/StatCard";
import { useComplianceStatusSummary } from "../hooks";
import type { ComplianceStatusCounts } from "../types";

const STATUS_TONES: Record<keyof ComplianceStatusCounts, Segment["tone"]> = {
  satisfied: "success",
  partial: "warning",
  no_coverage: "high",
  not_applicable: "neutral",
};

function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

function segmentsFor(counts: ComplianceStatusCounts): Segment[] {
  return (Object.keys(counts) as (keyof ComplianceStatusCounts)[]).map((key) => ({
    key,
    label: humanize(key),
    value: counts[key],
    tone: STATUS_TONES[key],
  }));
}

function SummaryCard({ label, counts }: { label: string; counts: ComplianceStatusCounts }) {
  // "Applicable" excludes controls the Statement of Applicability has
  // excluded -- an organization that legitimately doesn't run a given kind
  // of AI system shouldn't see its coverage percentage held down by that.
  const applicable = counts.satisfied + counts.partial + counts.no_coverage;
  const tone = counts.no_coverage > 0 ? "danger" : counts.partial > 0 ? "warning" : "success";

  return (
    <StatCard
      label={label}
      value={applicable > 0 ? `${counts.satisfied}/${applicable}` : "—"}
      hint={applicable > 0 ? "satisfied, of applicable controls" : "No applicable controls yet."}
      tone={applicable > 0 ? tone : "default"}
    >
      <SegmentedBar segments={segmentsFor(counts)} emptyLabel="No controls in this framework yet." />
    </StatCard>
  );
}

export function ComplianceSummaryCards() {
  const { data: summary, isLoading, isError } = useComplianceStatusSummary();

  if (isLoading) return <p>Loading compliance summary...</p>;
  if (isError || !summary) return <p>Failed to load compliance summary.</p>;

  return (
    <div className="dashboard-grid">
      <SummaryCard label="ISO 42001 Clauses" counts={summary.iso_42001_clauses} />
      <SummaryCard label="ISO 42001 Annex A" counts={summary.iso_42001_annex_a} />
      <SummaryCard label="EU AI Act" counts={summary.eu_ai_act} />
    </div>
  );
}
