import { AuditLogViewer } from "../../audit-log/components/AuditLogViewer";
import { DocumentBrowser } from "../../evidence/components/DocumentBrowser";
import { ChangesAsOf } from "../../changes/components/ChangesAsOf";
import { FrameworkTagPicker } from "../../framework-tags/components/FrameworkTagPicker";
import { ImprovementsAsOf } from "../../improvements/components/ImprovementsAsOf";
import { ObjectivesAsOf } from "../../objectives/components/ObjectivesAsOf";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useManagementReviewMeeting, useUpdateManagementReviewMeeting } from "../hooks";
import type { ManagementReviewMeetingUpdateInput } from "../types";

interface ManagementReviewMeetingDetailProps {
  meetingId: number;
}

type IsoFieldKey = Exclude<
  keyof ManagementReviewMeetingUpdateInput,
  "meeting_date" | "chaired_by" | "attendees"
>;

const ISO_FIELDS: { key: IsoFieldKey; label: string }[] = [
  { key: "previous_actions_status", label: "Status of actions from previous reviews" },
  { key: "context_changes", label: "Changes in internal and external issues" },
  {
    key: "performance_summary",
    label:
      "Performance: nonconformities and corrective actions, monitoring results, audit results, and achievement of AI objectives",
  },
  { key: "stakeholder_feedback", label: "Feedback from interested parties" },
  { key: "resource_adequacy", label: "Adequacy of resources" },
  { key: "improvement_opportunities", label: "Opportunities for continual improvement" },
  { key: "decisions_and_actions", label: "Decisions and actions" },
];

export function ManagementReviewMeetingDetail({ meetingId }: ManagementReviewMeetingDetailProps) {
  const { data: meeting, isLoading, isError } = useManagementReviewMeeting(meetingId);
  const { data: directory } = useUserDirectory();
  const updateMeeting = useUpdateManagementReviewMeeting(meetingId);

  if (isLoading) return <p>Loading meeting...</p>;
  if (isError || !meeting) return <p>Failed to load meeting.</p>;

  const chair = directory?.find((user) => user.id === meeting.chaired_by);

  return (
    <article>
      <header className="record-header">
        <div className="record-header-top">
          <h2>Management Review -- {meeting.meeting_date}</h2>
        </div>
      </header>

      <div>
        <label htmlFor="management-review-chair-edit">Chaired by</label>
        <select
          id="management-review-chair-edit"
          value={meeting.chaired_by ?? ""}
          onChange={(e) =>
            updateMeeting.mutate({ chaired_by: e.target.value ? Number(e.target.value) : null })
          }
        >
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
        {chair && <p>{formatUserOption(chair)}</p>}
      </div>

      <div>
        <label htmlFor="management-review-attendees-edit">Attendees</label>
        <input
          id="management-review-attendees-edit"
          defaultValue={meeting.attendees ?? ""}
          onBlur={(e) => updateMeeting.mutate({ attendees: e.target.value })}
        />
      </div>

      <ObjectivesAsOf asOf={meeting.meeting_date} />

      <ChangesAsOf asOf={meeting.meeting_date} />

      <ImprovementsAsOf asOf={meeting.meeting_date} />

      {ISO_FIELDS.map((field) => (
        <div key={field.key}>
          <h3>{field.label}</h3>
          <textarea
            aria-label={field.label}
            defaultValue={meeting[field.key] ?? ""}
            onBlur={(e) => updateMeeting.mutate({ [field.key]: e.target.value })}
          />
        </div>
      ))}

      <h3>Framework Tags</h3>
      <FrameworkTagPicker entityType="ManagementReviewMeeting" entityId={meetingId} />

      <h3>Minutes &amp; Slides</h3>
      <DocumentBrowser entityType="ManagementReviewMeeting" entityId={meetingId} />

      <AuditLogViewer entityType="ManagementReviewMeeting" entityId={meetingId} />
    </article>
  );
}
