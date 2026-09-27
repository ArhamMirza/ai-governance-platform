import { useParams } from "react-router-dom";

import { ManagementReviewMeetingDetail } from "../features/management-review/components/ManagementReviewMeetingDetail";

export function ManagementReviewMeetingDetailPage() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const id = Number(meetingId);

  if (!meetingId || Number.isNaN(id)) return <p>Invalid meeting id.</p>;

  return <ManagementReviewMeetingDetail meetingId={id} />;
}
