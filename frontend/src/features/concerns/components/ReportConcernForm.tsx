import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useConcernsProcess, useStaffAISystems, useSubmitConcern } from "../hooks";
import { CATEGORY_OPTIONS } from "../labels";
import type { ConcernSubmitted } from "../types";

const NOT_SURE = "not-sure";

const reportSchema = z.object({
  category: z.enum([
    "safety_or_harm",
    "bias_or_fairness",
    "privacy_or_data",
    "misuse_or_breach",
    "transparency",
    "accuracy_or_reliability",
    "other",
  ]),
  description: z.string().min(10, "Tell us a little more -- a sentence or two is enough"),
  ai_system: z.string(),
  system_note: z.string(),
  anonymous: z.boolean(),
});

type ReportValues = z.infer<typeof reportSchema>;

interface ReportConcernFormProps {
  onSubmitted: (result: ConcernSubmitted) => void;
}

/** Raising a concern -- by name, or anonymously. The wording says exactly what
 * anonymous means here, no more: nothing identifying is stored with the
 * concern, but what you write can still point to you. */
export function ReportConcernForm({ onSubmitted }: ReportConcernFormProps) {
  const submit = useSubmitConcern();
  const { data: systems } = useStaffAISystems();
  const { data: process } = useConcernsProcess();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ReportValues>({
    resolver: zodResolver(reportSchema),
    defaultValues: {
      category: "other",
      description: "",
      ai_system: NOT_SURE,
      system_note: "",
      anonymous: false,
    },
  });
  const anonymous = watch("anonymous");
  const unsure = watch("ai_system") === NOT_SURE;

  const onSubmit = handleSubmit((values) => {
    // The error shows from submit.error; nothing here needs to catch it.
    submit.mutate(
      {
        category: values.category,
        description: values.description.trim(),
        ai_system_row_id: values.ai_system === NOT_SURE ? null : Number(values.ai_system),
        system_note: values.ai_system === NOT_SURE ? values.system_note.trim() || null : null,
        anonymous: values.anonymous,
      },
      { onSuccess: (result) => onSubmitted(result) },
    );
  });

  return (
    <form onSubmit={onSubmit}>
      {process?.process_description && (
        <p className="approval-note">{process.process_description}</p>
      )}
      <div>
        <label htmlFor="concern-category">What is it about?</label>
        <select id="concern-category" {...register("category")}>
          {CATEGORY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label} -- {option.hint}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="concern-system">Which AI system?</label>
        <select id="concern-system" {...register("ai_system")}>
          <option value={NOT_SURE}>I'm not sure</option>
          {(systems ?? []).map((system) => (
            <option key={system.id} value={system.id}>
              {system.name}
            </option>
          ))}
        </select>
      </div>
      {unsure && (
        <div>
          <label htmlFor="concern-system-note">Where did you come across it?</label>
          <input id="concern-system-note" {...register("system_note")} />
        </div>
      )}
      <div>
        <label htmlFor="concern-description">What's your concern?</label>
        <textarea id="concern-description" rows={6} {...register("description")} />
        {errors.description && <p role="alert">{errors.description.message}</p>}
      </div>
      <fieldset>
        <legend>Who is this from?</legend>
        <label htmlFor="concern-anonymous">
          <input id="concern-anonymous" type="checkbox" {...register("anonymous")} />
          Report anonymously
        </label>
        <p className="approval-note">
          {anonymous
            ? "We won't store your name or account with this concern. You'll be given a tracking code to see what happens to it -- keep it somewhere safe, because it can't be shown again. Be aware that what you write can still point to you."
            : "Your name goes with this concern, so we can come back to you. You'll be able to follow it under My concerns."}
        </p>
      </fieldset>
      {submit.isError && (
        <p role="alert">{readError(submit.error, "Your concern couldn't be sent. Try again.")}</p>
      )}
      <button type="submit" disabled={submit.isPending}>
        {submit.isPending ? "Sending..." : "Send concern"}
      </button>
    </form>
  );
}
