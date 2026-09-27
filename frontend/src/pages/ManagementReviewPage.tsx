import { useState } from "react";

import { useCurrentUser } from "../features/auth/hooks";
import { hasPermission } from "../features/auth/permissions";
import { ManagementReviewMeetingForm } from "../features/management-review/components/ManagementReviewMeetingForm";
import { ManagementReviewMeetingList } from "../features/management-review/components/ManagementReviewMeetingList";
import { ManagementReviewSettingsPanel } from "../features/management-review/components/ManagementReviewSettingsPanel";

export function ManagementReviewPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: me } = useCurrentUser();
  const canEdit = hasPermission(me?.role, "edit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Management Review</h1>
          <p>Top-management review meetings, ISO/IEC 42001 Clause 9.3.</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? "Cancel" : "Record Meeting"}
          </button>
        )}
      </div>

      <ManagementReviewSettingsPanel />

      {showForm && <ManagementReviewMeetingForm onCreated={() => setShowForm(false)} />}

      <ManagementReviewMeetingList />
    </section>
  );
}
