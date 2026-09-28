import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useGovernanceRoles } from "../../governance-roles/hooks";
import { useCreateCompetenceRequirement } from "../hooks";

const requirementFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string(),
  governance_role_id: z.string(),
  refresh_interval_months: z
    .string()
    .refine((value) => value === "" || Number(value) >= 1, "Use a whole number of months"),
});

type RequirementFormValues = z.infer<typeof requirementFormSchema>;

interface CompetenceRequirementFormProps {
  onCreated?: (requirementId: number) => void;
}

export function CompetenceRequirementForm({ onCreated }: CompetenceRequirementFormProps) {
  const createRequirement = useCreateCompetenceRequirement();
  const { data: roles } = useGovernanceRoles();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<RequirementFormValues>({
    resolver: zodResolver(requirementFormSchema),
    defaultValues: { description: "", governance_role_id: "", refresh_interval_months: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    const requirement = await createRequirement.mutateAsync({
      title: values.title,
      description: values.description || null,
      governance_role_id: values.governance_role_id ? Number(values.governance_role_id) : null,
      refresh_interval_months: values.refresh_interval_months
        ? Number(values.refresh_interval_months)
        : null,
    });
    reset();
    onCreated?.(requirement.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="competence-title">Title</label>
        <input id="competence-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="competence-description">What it covers</label>
        <textarea id="competence-description" {...register("description")} />
      </div>
      <div>
        <label htmlFor="competence-applies-to">Applies to</label>
        <select id="competence-applies-to" {...register("governance_role_id")}>
          <option value="">Everyone</option>
          {(roles ?? []).map((role) => (
            <option key={role.id} value={role.id}>
              {role.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="competence-refresh">Refresh every (months, blank for once)</label>
        <input
          id="competence-refresh"
          type="number"
          min={1}
          {...register("refresh_interval_months")}
        />
        {errors.refresh_interval_months && (
          <p role="alert">{errors.refresh_interval_months.message}</p>
        )}
      </div>
      <button type="submit" disabled={createRequirement.isPending}>
        {createRequirement.isPending ? "Creating..." : "Create Requirement"}
      </button>
    </form>
  );
}
