import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateImprovement } from "../hooks";
import { SOURCE_OPTIONS } from "../labels";
import type { ImprovementSource, ImprovementSourceType } from "../types";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const SOURCES = SOURCE_OPTIONS.map((option) => option.value) as [
  ImprovementSource,
  ...ImprovementSource[],
];

const improvementFormSchema = z
  .object({
    title: z.string().min(1, "Describe the improvement in a few words"),
    description: z.string(),
    expected_benefit: z.string(),
    source: z.enum(SOURCES),
    owner_id: z.string(),
    raised_on: z.string().min(1, "When was it raised?"),
    target_date: z.string().min(1, "When should it be done by?"),
  })
  .refine((values) => !values.raised_on || values.target_date >= values.raised_on, {
    message: "The target date can't be before it was raised",
    path: ["target_date"],
  });

type ImprovementFormValues = z.infer<typeof improvementFormSchema>;

/** A record an improvement is being raised from -- see SourceImprovements. */
export interface ImprovementSourceRecord {
  sourceType: ImprovementSourceType;
  sourceId: number;
  /** What it's called, shown so the person knows what they're raising from. */
  label: string;
  /** Text to start the description from. Never set for a concern: nothing
   * of what was reported is carried into a record everyone can read. */
  description?: string;
}

interface ImprovementFormProps {
  from?: ImprovementSourceRecord;
  onCreated?: (improvementId: number) => void;
}

/** An opportunity to improve the AI management system (ISO/IEC 42001 10.1):
 * what, where it came from, who owns it and by when. */
export function ImprovementForm({ from, onCreated }: ImprovementFormProps) {
  const createImprovement = useCreateImprovement();
  const { data: directory } = useUserDirectory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ImprovementFormValues>({
    resolver: zodResolver(improvementFormSchema),
    defaultValues: {
      title: "",
      description: from?.description ?? "",
      expected_benefit: "",
      source: "idea",
      owner_id: "",
      raised_on: todayIso(),
      target_date: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    const improvement = await createImprovement.mutateAsync({
      title: values.title,
      description: values.description.trim() || null,
      expected_benefit: values.expected_benefit.trim() || null,
      // When raised from a record, the server sets the category from it.
      source: values.source,
      source_type: from?.sourceType ?? null,
      source_id: from?.sourceId ?? null,
      owner_id: values.owner_id ? Number(values.owner_id) : null,
      raised_on: values.raised_on,
      target_date: values.target_date,
    });
    reset();
    onCreated?.(improvement.id);
  });

  return (
    <form onSubmit={onSubmit}>
      {from ? (
        <p className="approval-note">Raised from {from.label}.</p>
      ) : (
        <div>
          <label htmlFor="improvement-source">Where it came from</label>
          <select id="improvement-source" {...register("source")}>
            {SOURCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      )}
      <div>
        <label htmlFor="improvement-title">Improvement</label>
        <input id="improvement-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="improvement-description">Description</label>
        <textarea id="improvement-description" {...register("description")} />
      </div>
      <div>
        <label htmlFor="improvement-benefit">Expected benefit</label>
        <textarea id="improvement-benefit" {...register("expected_benefit")} />
      </div>
      <div>
        <label htmlFor="improvement-owner">Owner</label>
        <select id="improvement-owner" {...register("owner_id")}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="improvement-raised-on">Raised on</label>
        <input id="improvement-raised-on" type="date" {...register("raised_on")} />
        {errors.raised_on && <p role="alert">{errors.raised_on.message}</p>}
      </div>
      <div>
        <label htmlFor="improvement-target-date">Target date</label>
        <input id="improvement-target-date" type="date" {...register("target_date")} />
        {errors.target_date && <p role="alert">{errors.target_date.message}</p>}
      </div>
      {createImprovement.isError && (
        <p role="alert">
          {readError(createImprovement.error, "Failed to add the improvement.")}
        </p>
      )}
      <button type="submit" disabled={createImprovement.isPending}>
        {createImprovement.isPending ? "Adding..." : "Add Improvement"}
      </button>
    </form>
  );
}
