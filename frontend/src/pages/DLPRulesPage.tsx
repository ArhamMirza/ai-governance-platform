import { useState } from "react";

import { AIToolsSubNav } from "../features/ai-use/components/AIToolsSubNav";
import { DLPRuleForm } from "../features/ai-use/components/DLPRuleForm";
import { DLPRuleList } from "../features/ai-use/components/DLPRuleList";
import { RuleTester } from "../features/ai-use/components/RuleTester";
import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";

export function DLPRulesPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Data rules</h1>
          <p>
            What must not be pasted or typed into AI tools. The browser extension checks text on the
            employee's own computer; the text never reaches this server.
          </p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Add Rule"}
          </button>
        )}
      </div>
      <AIToolsSubNav />
      {showForm && <DLPRuleForm onCreated={() => setShowForm(false)} />}

      <DLPRuleList />
      <RuleTester />
    </section>
  );
}
