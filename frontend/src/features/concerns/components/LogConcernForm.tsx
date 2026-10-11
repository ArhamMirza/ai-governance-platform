import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { aiSystemName } from "../../suppliers/labels";
import { useLogConcern } from "../hooks";
import { CATEGORY_OPTIONS, CHANNEL_OPTIONS } from "../labels";

const logSchema = z.object({
  channel: z.enum(["phone", "email", "in_person", "other"]),
  category: z.enum([
    "safety_or_harm",
    "bias_or_fairness",
    "privacy_or_data",
    "misuse_or_breach",
    "transparency",
    "accuracy_or_reliability",
    "other",
  ]),
  description: z.string().min(1, "Write down what was said"),
  received_on: z.string(),
  ai_system: z.string(),
  system_note: z.string(),
  anonymous: z.boolean(),
  reporter_note: z.string(),
});

type LogValues = z.infer<typeof logSchema>;

/** A concern raised some other way -- a call, an email, in person -- recorded
 * by a handler so everything lands in one register. */
export function LogConcernForm({ onLogged }: { onLogged?: (id: number) => void }) {
  const logConcern = useLogConcern();
  const { data: inventory } = useAISystemInventoryRows();
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<LogValues>({
    resolver: zodResolver(logSchema),
    defaultValues: {
      channel: "phone",
      category: "other",
      description: "",
      received_on: "",
      ai_system: "",
      system_note: "",
      anonymous: false,
      reporter_note: "",
    },
  });
  const anonymous = watch("anonymous");

  const onSubmit = handleSubmit(async (values) => {
    const concern = await logConcern.mutateAsync({
      channel: values.channel,
      category: values.category,
      description: values.description.trim(),
      received_on: values.received_on || null,
      ai_system_row_id: values.ai_system ? Number(values.ai_system) : null,
      system_note: values.system_note.trim() || null,
      anonymous: values.anonymous,
      reporter_note: values.anonymous ? null : values.reporter_note.trim() || null,
    });
    reset();
    onLogged?.(concern.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="log-channel">How was it raised?</label>
        <select id="log-channel" {...register("channel")}>
          {CHANNEL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="log-received-on">Received on</label>
        <input id="log-received-on" type="date" {...register("received_on")} />
        <span className="approval-note"> Leave blank for today.</span>
      </div>
      <div>
        <label htmlFor="log-category">What is it about?</label>
        <select id="log-category" {...register("category")}>
          {CATEGORY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="log-description">What was said</label>
        <textarea id="log-description" rows={4} {...register("description")} />
        {errors.description && <p role="alert">{errors.description.message}</p>}
      </div>
      <div>
        <label htmlFor="log-system">AI system</label>
        <select id="log-system" {...register("ai_system")}>
          <option value="">Not known</option>
          {(inventory?.rows ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {aiSystemName(row, row.id)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="log-system-note">Or describe it</label>
        <input id="log-system-note" {...register("system_note")} />
      </div>
      <fieldset>
        <legend>Who raised it?</legend>
        <label htmlFor="log-anonymous">
          <input id="log-anonymous" type="checkbox" {...register("anonymous")} />
          They asked to stay anonymous
        </label>
        {!anonymous && (
          <div>
            <label htmlFor="log-reporter-note">What they agreed to share</label>
            <input id="log-reporter-note" {...register("reporter_note")} />
          </div>
        )}
      </fieldset>
      {logConcern.isError && (
        <p role="alert">{readError(logConcern.error, "Failed to record the concern.")}</p>
      )}
      <button type="submit" disabled={logConcern.isPending}>
        {logConcern.isPending ? "Recording..." : "Record Concern"}
      </button>
    </form>
  );
}
