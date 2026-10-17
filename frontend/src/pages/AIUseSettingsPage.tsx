import { AIToolsSubNav } from "../features/ai-use/components/AIToolsSubNav";
import { AIUseSettingsPanel } from "../features/ai-use/components/AIUseSettingsPanel";
import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";

export function AIUseSettingsPage() {
  const { data: me } = useCurrentUser();
  const allowed = hasPermission(me?.role, "manage_settings");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>AI use settings</h1>
          <p>How the browser extension behaves, what staff are told, and the key it signs in with.</p>
        </div>
      </div>
      <AIToolsSubNav />
      {allowed ? <AIUseSettingsPanel /> : <p>Only administrators can change these settings.</p>}
    </section>
  );
}
