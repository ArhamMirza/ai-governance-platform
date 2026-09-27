import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useCreateAuditProgram } from "../hooks";

const auditProgramFormSchema = z
  .object({
    title: z.string().min(1, "Title is required"),
    description: z.string().optional(),
    schedule_type: z.enum(["interval", "ad_hoc"]),
    interval_months: z.string().optional(),
    start_date: z.string().optional(),
  })
  .refine(
    (values) => values.schedule_type !== "interval" || Number(values.interval_months) > 0,
    { message: "An interval-based program needs an interval, in months", path: ["interval_months"] },
  );

type AuditProgramFormValues = z.infer<typeof auditProgramFormSchema>;

interface AuditProgramFormProps {
  onCreated?: (programId: number) => void;
}

export function AuditProgramForm({ onCreated }: AuditProgramFormProps) {
  const createAuditProgram = useCreateAuditProgram();
  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<AuditProgramFormValues>({
    resolver: zodResolver(auditProgramFormSchema),
    defaultValues: { schedule_type: "interval" },
  });
  const scheduleType = watch("schedule_type");

  const onSubmit = handleSubmit(async (values) => {
    const program = await createAuditProgram.mutateAsync({
      title: values.title,
      description: values.description || null,
      schedule_type: values.schedule_type,
      interval_months:
        values.schedule_type === "interval" ? Number(values.interval_months) : null,
      start_date: values.start_date || null,
    });
    reset();
    onCreated?.(program.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="audit-program-title">Title</label>
        <input id="audit-program-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="audit-program-description">Scope</label>
        <textarea id="audit-program-description" {...register("description")} />
      </div>
      <fieldset>
        <legend>Schedule</legend>
        <label>
          <input type="radio" value="interval" {...register("schedule_type")} />
          Recurring, on an interval
        </label>
        <label>
          <input type="radio" value="ad_hoc" {...register("schedule_type")} />
          Ad hoc -- a one-off audit
        </label>
      </fieldset>
      {scheduleType === "interval" && (
        <div>
          <label htmlFor="audit-program-interval">Every how many months</label>
          <input
            id="audit-program-interval"
            type="number"
            min={1}
            {...register("interval_months")}
          />
          {errors.interval_months && <p role="alert">{errors.interval_months.message}</p>}
        </div>
      )}
      <div>
        <label htmlFor="audit-program-start-date">
          {scheduleType === "interval" ? "First audit due" : "Planned date"}
        </label>
        <input id="audit-program-start-date" type="date" {...register("start_date")} />
      </div>
      <button type="submit" disabled={createAuditProgram.isPending}>
        {createAuditProgram.isPending ? "Creating..." : "Create Audit Program"}
      </button>
    </form>
  );
}
