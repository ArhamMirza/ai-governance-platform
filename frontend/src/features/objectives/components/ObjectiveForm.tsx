import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { usePolicies } from "../../policies/hooks";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateObjective } from "../hooks";
import { DIRECTION_OPTIONS, KIND_OPTIONS } from "../labels";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const objectiveFormSchema = z
  .object({
    title: z.string().min(1, "Title is required"),
    kind: z.enum(["measured", "milestone"]),
    description: z.string(),
    owner_id: z.string(),
    policy_id: z.string(),
    established_on: z.string().min(1, "When was the objective set?"),
    target_date: z.string(),
    metric_name: z.string(),
    unit: z.string(),
    direction: z.enum(["at_least", "at_most"]),
    target_value: z.string(),
    baseline_value: z.string(),
    measurement_interval_months: z.string(),
    first_measurement_due: z.string(),
  })
  .superRefine((values, ctx) => {
    const issue = (path: string, message: string) =>
      ctx.addIssue({ code: "custom", path: [path], message });
    if (values.kind === "milestone") {
      if (!values.target_date) issue("target_date", "A milestone needs a target date");
      return;
    }
    if (!values.metric_name) issue("metric_name", "What's being measured?");
    if (values.target_value === "" || Number.isNaN(Number(values.target_value))) {
      issue("target_value", "Enter the target as a number");
    }
    if ((values.measurement_interval_months === "") !== (values.first_measurement_due === "")) {
      issue("first_measurement_due", "Set both how often and when the first reading is due, or neither");
    }
  })
  .refine((values) => !values.target_date || values.target_date >= values.established_on, {
    message: "The target date can't be before the objective was set",
    path: ["target_date"],
  });

type ObjectiveFormValues = z.infer<typeof objectiveFormSchema>;

const numberOrNull = (value: string) => (value === "" ? null : Number(value));

interface ObjectiveFormProps {
  onCreated?: (objectiveId: number) => void;
}

/** The objective and how it's measured -- the 6.2 plan (actions, resources,
 * evaluation), linked AI systems and readings are added on the detail page. */
export function ObjectiveForm({ onCreated }: ObjectiveFormProps) {
  const createObjective = useCreateObjective();
  const { data: directory } = useUserDirectory();
  const { data: policies } = usePolicies();
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<ObjectiveFormValues>({
    resolver: zodResolver(objectiveFormSchema),
    defaultValues: {
      kind: "measured",
      description: "",
      owner_id: "",
      policy_id: "",
      established_on: todayIso(),
      target_date: "",
      metric_name: "",
      unit: "",
      direction: "at_least",
      target_value: "",
      baseline_value: "",
      measurement_interval_months: "",
      first_measurement_due: "",
    },
  });
  const measured = watch("kind") === "measured";

  const onSubmit = handleSubmit(async (values) => {
    const objective = await createObjective.mutateAsync({
      title: values.title,
      kind: values.kind,
      description: values.description || null,
      owner_id: values.owner_id ? Number(values.owner_id) : null,
      policy_id: values.policy_id ? Number(values.policy_id) : null,
      established_on: values.established_on,
      target_date: values.target_date || null,
      planned_actions: null,
      resources: null,
      evaluation_method: null,
      metric_name: measured ? values.metric_name : null,
      unit: measured ? values.unit || null : null,
      direction: measured ? values.direction : null,
      target_value: measured ? numberOrNull(values.target_value) : null,
      baseline_value: measured ? numberOrNull(values.baseline_value) : null,
      measurement_interval_months: measured ? numberOrNull(values.measurement_interval_months) : null,
      first_measurement_due: measured ? values.first_measurement_due || null : null,
    });
    reset();
    onCreated?.(objective.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="objective-title">Objective</label>
        <input id="objective-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <fieldset>
        <legend>Kind</legend>
        {KIND_OPTIONS.map((option) => (
          <label key={option.value}>
            <input type="radio" value={option.value} {...register("kind")} />
            {option.label} <span className="approval-note">{option.hint}</span>
          </label>
        ))}
      </fieldset>
      <div>
        <label htmlFor="objective-description">Description</label>
        <textarea id="objective-description" {...register("description")} />
      </div>
      <div>
        <label htmlFor="objective-owner">Owner</label>
        <select id="objective-owner" {...register("owner_id")}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="objective-policy">Supports policy</label>
        <select id="objective-policy" {...register("policy_id")}>
          <option value="">None</option>
          {(policies ?? []).map((policy) => (
            <option key={policy.id} value={policy.id}>
              {policy.title}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="objective-established-on">Set on</label>
        <input id="objective-established-on" type="date" {...register("established_on")} />
        {errors.established_on && <p role="alert">{errors.established_on.message}</p>}
      </div>
      <div>
        <label htmlFor="objective-target-date">Target date</label>
        <input id="objective-target-date" type="date" {...register("target_date")} />
        {errors.target_date && <p role="alert">{errors.target_date.message}</p>}
      </div>

      {measured && (
        <fieldset>
          <legend>Measurement</legend>
          <div>
            <label htmlFor="objective-metric">Metric</label>
            <input id="objective-metric" {...register("metric_name")} />
            {errors.metric_name && <p role="alert">{errors.metric_name.message}</p>}
          </div>
          <div>
            <label htmlFor="objective-direction">Target</label>
            <select id="objective-direction" {...register("direction")}>
              {DIRECTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <label htmlFor="objective-target-value">Target value</label>
            <input
              id="objective-target-value"
              type="number"
              step="any"
              {...register("target_value")}
            />
            <label htmlFor="objective-unit">Unit</label>
            <input id="objective-unit" placeholder="%, days, count" {...register("unit")} />
            {errors.target_value && <p role="alert">{errors.target_value.message}</p>}
          </div>
          <div>
            <label htmlFor="objective-baseline">Baseline (where it started)</label>
            <input
              id="objective-baseline"
              type="number"
              step="any"
              {...register("baseline_value")}
            />
          </div>
          <div>
            <label htmlFor="objective-interval">Measure every (months)</label>
            <input
              id="objective-interval"
              type="number"
              min={1}
              {...register("measurement_interval_months")}
            />
            <label htmlFor="objective-first-due">First reading due</label>
            <input id="objective-first-due" type="date" {...register("first_measurement_due")} />
            {errors.first_measurement_due && (
              <p role="alert">{errors.first_measurement_due.message}</p>
            )}
          </div>
        </fieldset>
      )}

      {createObjective.isError && (
        <p role="alert">{readError(createObjective.error, "Failed to add the objective.")}</p>
      )}
      <button type="submit" disabled={createObjective.isPending}>
        {createObjective.isPending ? "Adding..." : "Add Objective"}
      </button>
    </form>
  );
}
