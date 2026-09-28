import { Link } from "react-router-dom";

import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useManagementReviewMeetings } from "../hooks";

export function ManagementReviewMeetingList() {
  const { data: meetings, isLoading, isError } = useManagementReviewMeetings();
  const { data: directory } = useUserDirectory();

  if (isLoading) return <p>Loading meetings...</p>;
  if (isError) return <p>Failed to load meetings.</p>;
  if (!meetings || meetings.length === 0) return <p>No management review meetings recorded yet.</p>;

  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Chaired by</th>
        </tr>
      </thead>
      <tbody>
        {meetings.map((meeting) => {
          const chair = directory?.find((user) => user.id === meeting.chaired_by);
          return (
            <tr key={meeting.id}>
              <td data-type="date">
                <Link to={`/management-review/${meeting.id}`}>{meeting.meeting_date}</Link>
              </td>
              <td>{chair ? formatUserOption(chair) : "Unassigned"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
