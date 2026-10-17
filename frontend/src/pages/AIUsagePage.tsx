import { AIToolsSubNav } from "../features/ai-use/components/AIToolsSubNav";
import { UsagePanel } from "../features/ai-use/components/UsagePanel";
import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";

export function AIUsagePage() {
  const { data: me } = useCurrentUser();
  const allowed = hasPermission(me?.role, "manage_settings");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>AI usage</h1>
          <p>
            How often staff open AI sites that aren't approved, and what the data rules caught.
            Counts only: never what was typed, which page, or when in the day.
          </p>
        </div>
      </div>
      <AIToolsSubNav />
      {allowed ? (
        <UsagePanel />
      ) : (
        <p>Only administrators can see who used what.</p>
      )}
    </section>
  );
}
