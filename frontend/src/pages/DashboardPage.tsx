import { GettingStartedPanel } from "../features/dashboard/components/GettingStartedPanel";
import { DashboardSummaryView } from "../features/dashboard/components/DashboardSummaryView";
import { useHealthCheck } from "../shared/hooks/useHealthCheck";

export function DashboardPage() {
  const { data, isLoading, isError } = useHealthCheck();

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>
            Backend status:{" "}
            {isLoading ? "checking..." : isError ? "unreachable" : data?.status}
          </p>
        </div>
      </div>

      <GettingStartedPanel />

      <DashboardSummaryView />
    </section>
  );
}
