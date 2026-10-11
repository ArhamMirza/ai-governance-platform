import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateChange } from "../hooks";
import { CHANGE_TYPE_OPTIONS } from "../labels";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const changeFormSchema = z
  .object({
    title: z.string().min(1, "Describe the change in a few words"),
    change_type: z.enum(["ai_system", "process", "policy", "organization", "other"]),
    reason: z.string(),
    consequences: z.string(),
    resources_needed: z.string(),
    owner_id: z.string(),
    raised_on: z.string().min(1, "When was it raised?"),
    planned_date: z.string().min(1, "When is it planned for?"),
  })
  .refine((values) => !values.raised_on || values.planned_date >= values.raised_on, {
    message: "The planned date can't be before the change was raised",
    path: ["planned_date"],
  });

type ChangeFormValues = z.infer<typeof changeFormSchema>;

interface ChangeFormProps {
  onCreated?: (changeId: number) => void;
}

/** What is changing, why, and what it affects (ISO/IEC 42001 6.3) -- linked
 * AI systems are added on the detail page. */
export function ChangeForm({ onCreated }: ChangeFormProps) {
  const createChange = useCreateChange();
  const { data: directory } = useUserDirectory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangeFormValues>({
    resolver: zodResolver(changeFormSchema),
    defaultValues: {
      change_type: "other",
      reason: "",
      consequences: "",
      resources_needed: "",
      owner_id: "",
      raised_on: todayIso(),
      planned_date: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    const change = await createChange.mutateAsync({
      title: values.title,
      description: null,
      change_type: values.change_type,
      reason: values.reason || null,
      consequences: values.consequences || null,
      resources_needed: values.resources_needed || null,
      owner_id: values.owner_id ? Number(values.owner_id) : null,
      raised_on: values.raised_on,
      planned_date: values.planned_date,
    });
    reset();
    onCreated?.(change.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="change-title">Change</label>
        <input id="change-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="change-type">What it concerns</label>
        <select id="change-type" {...register("change_type")}>
          {CHANGE_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="change-reason">Why</label>
        <textarea id="change-reason" {...register("reason")} />
      </div>
      <div>
        <label htmlFor="change-consequences">Potential consequences</label>
        <textarea id="change-consequences" {...register("consequences")} />
      </div>
      <div>
        <label htmlFor="change-resources">Resources needed</label>
        <textarea id="change-resources" {...register("resources_needed")} />
      </div>
      <div>
        <label htmlFor="change-owner">Owner</label>
        <select id="change-owner" {...register("owner_id")}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="change-raised-on">Raised on</label>
        <input id="change-raised-on" type="date" {...register("raised_on")} />
        {errors.raised_on && <p role="alert">{errors.raised_on.message}</p>}
      </div>
      <div>
        <label htmlFor="change-planned-date">Planned for</label>
        <input id="change-planned-date" type="date" {...register("planned_date")} />
        {errors.planned_date && <p role="alert">{errors.planned_date.message}</p>}
      </div>
      {createChange.isError && (
        <p role="alert">{readError(createChange.error, "Failed to add the change.")}</p>
      )}
      <button type="submit" disabled={createChange.isPending}>
        {createChange.isPending ? "Adding..." : "Add Change"}
      </button>
    </form>
  );
}
