import { AiSettingsForm } from "../features/ai-assist/components/AiSettingsForm";
import { AiSpendPanel } from "../features/ai-assist/components/AiSpendPanel";

export function SettingsPage() {
  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Organization-wide configuration. Only admins can change these.</p>
        </div>
      </div>

      <AiSettingsForm />
      <AiSpendPanel />
    </section>
  );
}
