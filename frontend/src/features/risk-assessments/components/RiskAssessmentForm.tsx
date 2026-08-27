import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAISystemInventoryRows, useCreateRiskAssessment } from "../hooks";

const riskAssessmentFormSchema = z.object({
  ai_system_row_id: z.string().min(1, "Select an AI System"),
});

type RiskAssessmentFormValues = z.infer<typeof riskAssessmentFormSchema>;

interface RiskAssessmentFormProps {
  onCreated?: (riskAssessmentId: number) => void;
}

export function RiskAssessmentForm({ onCreated }: RiskAssessmentFormProps) {
  const createRiskAssessment = useCreateRiskAssessment();
  const { data: inventory } = useAISystemInventoryRows();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<RiskAssessmentFormValues>({ resolver: zodResolver(riskAssessmentFormSchema) });

  const onSubmit = handleSubmit(async (values) => {
    const riskAssessment = await createRiskAssessment.mutateAsync({
      ai_system_row_id: Number(values.ai_system_row_id),
    });
    reset();
    onCreated?.(riskAssessment.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="risk-assessment-ai-system">AI System</label>
        <select id="risk-assessment-ai-system" {...register("ai_system_row_id")}>
          <option value="">Select an AI System</option>
          {inventory?.rows.map((row) => (
            <option key={row.id} value={row.id}>
              {typeof row.data.name === "string" && row.data.name
                ? row.data.name
                : `AI System #${row.id}`}
            </option>
          ))}
        </select>
        {errors.ai_system_row_id && <p role="alert">{errors.ai_system_row_id.message}</p>}
      </div>
      <p>Framework tags are added from the assessment's detail page once it's created.</p>
      <button type="submit" disabled={createRiskAssessment.isPending}>
        {createRiskAssessment.isPending ? "Creating..." : "Create Risk Assessment"}
      </button>
    </form>
  );
}
