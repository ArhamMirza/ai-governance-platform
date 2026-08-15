import { DashboardSummaryView } from "../features/dashboard/components/DashboardSummaryView";
import { useHealthCheck } from "../shared/hooks/useHealthCheck";

export function DashboardPage() {
  const { data, isLoading, isError } = useHealthCheck();

  return (
    <section>
      <h1>Dashboard</h1>
      <p>
        Backend status:{" "}
        {isLoading ? "checking..." : isError ? "unreachable" : data?.status}
      </p>

      <DashboardSummaryView />
    </section>
  );
}
