import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { CLASSIFICATION_OPTIONS } from "../../ai-tools/labels";
import { useBuiltinDetectors, useCreateDLPRule } from "../hooks";
import { ACTION_OPTIONS, KIND_LABELS, splitKeywords } from "../labels";

const ruleFormSchema = z
  .object({
    name: z.string().trim().min(1, "Name the rule"),
    description: z.string(),
    kind: z.enum(["builtin", "keywords", "regex"]),
    builtin_key: z.string(),
    keywords: z.string(),
    pattern: z.string(),
    classification: z.enum(["public", "internal", "confidential"]),
    action: z.enum(["monitor", "warn", "block"]),
  })
  .superRefine((values, context) => {
    if (values.kind === "builtin" && !values.builtin_key) {
      context.addIssue({ code: "custom", path: ["builtin_key"], message: "Choose what to look for" });
    }
    if (values.kind === "keywords" && splitKeywords(values.keywords).length === 0) {
      context.addIssue({ code: "custom", path: ["keywords"], message: "Add at least one word or phrase" });
    }
    if (values.kind === "regex" && !values.pattern.trim()) {
      context.addIssue({ code: "custom", path: ["pattern"], message: "Enter the pattern" });
    }
  });

type RuleFormValues = z.infer<typeof ruleFormSchema>;

/** A new data-loss-prevention rule. The server checks the pattern is safe to
 * run in a browser and says why when it isn't. */
export function DLPRuleForm({ onCreated }: { onCreated?: (ruleId: number) => void }) {
  const createRule = useCreateDLPRule();
  const { data: detectors } = useBuiltinDetectors();
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<RuleFormValues>({
    resolver: zodResolver(ruleFormSchema),
    defaultValues: {
      name: "",
      description: "",
      kind: "builtin",
      builtin_key: "",
      keywords: "",
      pattern: "",
      classification: "confidential",
      action: "block",
    },
  });
  const kind = watch("kind");
  const builtinKey = watch("builtin_key");
  const detector = detectors?.find((candidate) => candidate.key === builtinKey);

  const onSubmit = handleSubmit((values) => {
    createRule.mutate(
      {
        name: values.name,
        description: values.description.trim() || null,
        kind: values.kind,
        builtin_key: values.kind === "builtin" ? values.builtin_key : null,
        keywords: values.kind === "keywords" ? splitKeywords(values.keywords) : null,
        pattern: values.kind === "regex" ? values.pattern.trim() : null,
        classification: values.classification,
        action: values.action,
        enabled: true,
      },
      {
        onSuccess: (rule) => {
          reset();
          onCreated?.(rule.id);
        },
      },
    );
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="rule-name">Rule</label>
        <input id="rule-name" {...register("name")} />
        {errors.name && <p role="alert">{errors.name.message}</p>}
      </div>
      <div>
        <label htmlFor="rule-kind">What it looks for</label>
        <select id="rule-kind" {...register("kind")}>
          {(Object.keys(KIND_LABELS) as (keyof typeof KIND_LABELS)[]).map((value) => (
            <option key={value} value={value}>
              {KIND_LABELS[value]}
            </option>
          ))}
        </select>
      </div>
      {kind === "builtin" && (
        <div>
          <label htmlFor="rule-detector">Detector</label>
          <select id="rule-detector" {...register("builtin_key")}>
            <option value="">Choose one</option>
            {(detectors ?? []).map((candidate) => (
              <option key={candidate.key} value={candidate.key}>
                {candidate.label}
              </option>
            ))}
          </select>
          {detector && <p className="approval-note">{detector.description}</p>}
          {errors.builtin_key && <p role="alert">{errors.builtin_key.message}</p>}
        </div>
      )}
      {kind === "keywords" && (
        <div>
          <label htmlFor="rule-keywords">Words and phrases</label>
          <textarea id="rule-keywords" {...register("keywords")} />
          <p className="approval-note">
            One per line. Matched ignoring case, and only as whole words.
          </p>
          {errors.keywords && <p role="alert">{errors.keywords.message}</p>}
        </div>
      )}
      {kind === "regex" && (
        <div>
          <label htmlFor="rule-pattern">Pattern</label>
          <input id="rule-pattern" {...register("pattern")} />
          <p className="approval-note">
            A regular expression. Groups that repeat inside repeats, back-references and look-behinds
            are refused, because they can freeze a browser.
          </p>
          {errors.pattern && <p role="alert">{errors.pattern.message}</p>}
        </div>
      )}
      <div>
        <label htmlFor="rule-classification">How sensitive the data is</label>
        <select id="rule-classification" {...register("classification")}>
          {CLASSIFICATION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <p className="approval-note">
          A tool approved for this class of data, or a higher one, is not held to the rule.
        </p>
      </div>
      <div>
        <label htmlFor="rule-action">When it matches</label>
        <select id="rule-action" {...register("action")}>
          {ACTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label} -- {option.hint}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="rule-description">Why it exists</label>
        <textarea id="rule-description" {...register("description")} />
      </div>
      {createRule.isError && (
        <p role="alert">{readError(createRule.error, "Failed to add the rule.")}</p>
      )}
      <button type="submit" disabled={createRule.isPending}>
        {createRule.isPending ? "Adding..." : "Add Rule"}
      </button>
    </form>
  );
}
