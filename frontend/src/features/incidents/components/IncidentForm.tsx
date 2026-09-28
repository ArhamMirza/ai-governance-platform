import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateIncident } from "../hooks";
import { SEVERITY_OPTIONS, aiSystemName } from "../labels";

const incidentFormSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().min(1, "Describe what happened"),
  ai_system_row_id: z.string(),
  detected_on: z.string().min(1, "When did you become aware of it?"),
  occurred_on: z.string(),
  severity: z.enum(["low", "medium", "high", "critical"]),
  owner_id: z.string(),
});

type IncidentFormValues = z.infer<typeof incidentFormSchema>;

interface IncidentFormProps {
  onCreated?: (incidentId: number) => void;
}

/** Just enough to log it fast -- impact, root cause and whether it's a
 * reportable serious incident are filled in on the detail page. */
export function IncidentForm({ onCreated }: IncidentFormProps) {
  const createIncident = useCreateIncident();
  const { data: inventory } = useAISystemInventoryRows();
  const { data: directory } = useUserDirectory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<IncidentFormValues>({
    resolver: zodResolver(incidentFormSchema),
    defaultValues: { severity: "medium", ai_system_row_id: "", occurred_on: "", owner_id: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    const incident = await createIncident.mutateAsync({
      title: values.title,
      description: values.description,
      ai_system_row_id: values.ai_system_row_id ? Number(values.ai_system_row_id) : null,
      detected_on: values.detected_on,
      occurred_on: values.occurred_on || null,
      severity: values.severity,
      owner_id: values.owner_id ? Number(values.owner_id) : null,
    });
    reset();
    onCreated?.(incident.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="incident-title">Title</label>
        <input id="incident-title" {...register("title")} />
        {errors.title && <p role="alert">{errors.title.message}</p>}
      </div>
      <div>
        <label htmlFor="incident-description">What happened</label>
        <textarea id="incident-description" {...register("description")} />
        {errors.description && <p role="alert">{errors.description.message}</p>}
      </div>
      <div>
        <label htmlFor="incident-ai-system">AI system</label>
        <select id="incident-ai-system" {...register("ai_system_row_id")}>
          <option value="">Not about one system</option>
          {(inventory?.rows ?? []).map((row) => (
            <option key={row.id} value={row.id}>
              {aiSystemName(row, row.id)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="incident-detected-on">Detected on</label>
        <input id="incident-detected-on" type="date" {...register("detected_on")} />
        {errors.detected_on && <p role="alert">{errors.detected_on.message}</p>}
      </div>
      <div>
        <label htmlFor="incident-occurred-on">Occurred on (if known)</label>
        <input id="incident-occurred-on" type="date" {...register("occurred_on")} />
      </div>
      <div>
        <label htmlFor="incident-severity">Severity</label>
        <select id="incident-severity" {...register("severity")}>
          {SEVERITY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="incident-owner">Handled by</label>
        <select id="incident-owner" {...register("owner_id")}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <button type="submit" disabled={createIncident.isPending}>
        {createIncident.isPending ? "Logging..." : "Log Incident"}
      </button>
    </form>
  );
}
