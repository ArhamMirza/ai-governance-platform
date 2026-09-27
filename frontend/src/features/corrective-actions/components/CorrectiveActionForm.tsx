import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateCorrectiveAction } from "../hooks";

const correctiveActionFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  nonconformity_description: z.string().min(1, "Describe the nonconformity"),
  assignee_id: z.string().min(1, "Assign someone to this corrective action"),
  due_date: z.string().min(1, "A due date is required"),
});

type CorrectiveActionFormValues = z.infer<typeof correctiveActionFormSchema>;

interface CorrectiveActionFormProps {
  onCreated?: (correctiveActionId: number) => void;
  /** Pre-fills the form when raised from somewhere with its own context to
   * offer -- e.g. an audit finding. The source link travels through to the
   * created record; everything else (who's responsible, when it's due)
   * stays a deliberate choice the person filling the form makes. */
  initialTitle?: string;
  initialNonconformityDescription?: string;
  sourceType?: string;
  sourceId?: number;
}

export function CorrectiveActionForm({
  onCreated,
  initialTitle,
  initialNonconformityDescription,
  sourceType,
  sourceId,
}: CorrectiveActionFormProps) {
  const createCorrectiveAction = useCreateCorrectiveAction();
  const { data: directory } = useUserDirectory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CorrectiveActionFormValues>({
    resolver: zodResolver(correctiveActionFormSchema),
    defaultValues: {
      title: initialTitle,
      nonconformity_description: initialNonconformityDescription,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    const correctiveAction = await createCorrectiveAction.mutateAsync({
      title: values.title,
      nonconformity_description: values.nonconformity_description,
      assignee_id: Number(values.assignee_id),
      due_date: values.due_date,
      source_type: sourceType,
      source_id: sourceId,
    });
    reset();
    onCreated?.(correctiveAction.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="corrective-action-title">Title</label>
        <input id="corrective-action-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="corrective-action-nonconformity">Nonconformity</label>
        <textarea
          id="corrective-action-nonconformity"
          {...register("nonconformity_description")}
        />
        {errors.nonconformity_description && (
          <p role="alert">{errors.nonconformity_description.message}</p>
        )}
      </div>
      <div>
        <label htmlFor="corrective-action-assignee">Assignee</label>
        <select id="corrective-action-assignee" {...register("assignee_id")}>
          <option value="">Choose who's responsible</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
        {errors.assignee_id && <p role="alert">{errors.assignee_id.message}</p>}
      </div>
      <div>
        <label htmlFor="corrective-action-due-date">Due date</label>
        <input id="corrective-action-due-date" type="date" {...register("due_date")} />
        {errors.due_date && <p role="alert">{errors.due_date.message}</p>}
      </div>
      <button type="submit" disabled={createCorrectiveAction.isPending}>
        {createCorrectiveAction.isPending ? "Creating..." : "Create Corrective Action"}
      </button>
    </form>
  );
}
