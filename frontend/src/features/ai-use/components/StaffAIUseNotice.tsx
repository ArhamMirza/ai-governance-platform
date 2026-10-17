import { useStaffAIUseNotice } from "../hooks";

const ON_UNAPPROVED = {
  monitor: "Opening an AI website that hasn't been approved is counted.",
  warn: "Opening an AI website that hasn't been approved shows you a warning first.",
  block: "AI websites that haven't been approved are blocked.",
} as const;

/** What staff are told about how their use of AI tools is monitored -- shown
 * on their AI tools page, so no one has to guess. */
export function StaffAIUseNotice() {
  const { data: notice } = useStaffAIUseNotice();

  if (!notice) return null;
  return (
    <section aria-label="How AI use is monitored" className="reporter-concern">
      <h3>How your use of AI tools is monitored</h3>
      <p>{ON_UNAPPROVED[notice.unapproved_site_action]}</p>
      {notice.staff_notice ? (
        <p>{notice.staff_notice}</p>
      ) : (
        <p className="approval-note">
          Nothing has been published about monitoring yet. Ask the governance team.
        </p>
      )}
    </section>
  );
}
