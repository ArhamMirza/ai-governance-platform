import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateManagementReviewMeeting } from "../hooks";

const meetingFormSchema = z.object({
  meeting_date: z.string().min(1, "A meeting date is required"),
  chaired_by: z.string().optional(),
  attendees: z.string().optional(),
});

type MeetingFormValues = z.infer<typeof meetingFormSchema>;

interface ManagementReviewMeetingFormProps {
  onCreated?: (meetingId: number) => void;
}

export function ManagementReviewMeetingForm({ onCreated }: ManagementReviewMeetingFormProps) {
  const createMeeting = useCreateManagementReviewMeeting();
  const { data: directory } = useUserDirectory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<MeetingFormValues>({ resolver: zodResolver(meetingFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    const meeting = await createMeeting.mutateAsync({
      meeting_date: values.meeting_date,
      chaired_by: values.chaired_by ? Number(values.chaired_by) : null,
      attendees: values.attendees || null,
    });
    reset();
    onCreated?.(meeting.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="management-review-meeting-date">Meeting date</label>
        <input id="management-review-meeting-date" type="date" {...register("meeting_date")} />
        {errors.meeting_date && <p role="alert">{errors.meeting_date.message}</p>}
      </div>
      <div>
        <label htmlFor="management-review-meeting-chair">Chaired by</label>
        <select id="management-review-meeting-chair" {...register("chaired_by")}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="management-review-meeting-attendees">Attendees</label>
        <input id="management-review-meeting-attendees" {...register("attendees")} />
      </div>
      <p>The ISO-required inputs and decisions are recorded from the meeting's own page.</p>
      <button type="submit" disabled={createMeeting.isPending}>
        {createMeeting.isPending ? "Creating..." : "Record Meeting"}
      </button>
    </form>
  );
}
