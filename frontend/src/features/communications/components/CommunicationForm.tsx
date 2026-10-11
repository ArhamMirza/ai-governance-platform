import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { formatUserOption } from "../../users/formatUserOption";
import { useUserDirectory } from "../../users/hooks";
import { useCreateCommunication } from "../hooks";
import { DIRECTION_OPTIONS } from "../labels";

const communicationFormSchema = z
  .object({
    topic: z.string().min(1, "What is being communicated?"),
    audience: z.string().min(1, "Who is it for?"),
    direction: z.enum(["internal", "external"]),
    method: z.string(),
    responsible_id: z.string(),
    notes: z.string(),
    interval_months: z.string(),
    first_due: z.string(),
  })
  .refine((values) => (values.interval_months === "") === (values.first_due === ""), {
    message: "Set both how often and when it's first due, or neither (done only when needed)",
    path: ["first_due"],
  });

type CommunicationFormValues = z.infer<typeof communicationFormSchema>;

interface CommunicationFormProps {
  onCreated?: (id: number) => void;
}

/** One planned communication: on what, with whom, how, and how often
 * (ISO/IEC 42001 7.4). When it was actually done is recorded on its page. */
export function CommunicationForm({ onCreated }: CommunicationFormProps) {
  const createCommunication = useCreateCommunication();
  const { data: directory } = useUserDirectory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CommunicationFormValues>({
    resolver: zodResolver(communicationFormSchema),
    defaultValues: {
      direction: "internal",
      method: "",
      responsible_id: "",
      notes: "",
      interval_months: "",
      first_due: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    const item = await createCommunication.mutateAsync({
      topic: values.topic,
      audience: values.audience,
      direction: values.direction,
      method: values.method || null,
      responsible_id: values.responsible_id ? Number(values.responsible_id) : null,
      notes: values.notes || null,
      interval_months: values.interval_months ? Number(values.interval_months) : null,
      first_due: values.first_due || null,
    });
    reset();
    onCreated?.(item.id);
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="communication-topic">What is communicated</label>
        <input id="communication-topic" {...register("topic")} />
        {errors.topic && <p role="alert">{errors.topic.message}</p>}
      </div>
      <div>
        <label htmlFor="communication-audience">To whom</label>
        <input id="communication-audience" {...register("audience")} />
        {errors.audience && <p role="alert">{errors.audience.message}</p>}
      </div>
      <div>
        <label htmlFor="communication-direction">Inside or outside the organization</label>
        <select id="communication-direction" {...register("direction")}>
          {DIRECTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="communication-method">How</label>
        <input id="communication-method" {...register("method")} />
      </div>
      <div>
        <label htmlFor="communication-responsible">Responsible</label>
        <select id="communication-responsible" {...register("responsible_id")}>
          <option value="">Unassigned</option>
          {(directory ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {formatUserOption(user)}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="communication-interval">Every (months)</label>
        <input
          id="communication-interval"
          type="number"
          min={1}
          {...register("interval_months")}
        />
        <label htmlFor="communication-first-due">First due</label>
        <input id="communication-first-due" type="date" {...register("first_due")} />
        {errors.first_due && <p role="alert">{errors.first_due.message}</p>}
      </div>
      <div>
        <label htmlFor="communication-notes">Notes</label>
        <textarea id="communication-notes" {...register("notes")} />
      </div>
      {createCommunication.isError && (
        <p role="alert">
          {readError(createCommunication.error, "Failed to add the communication.")}
        </p>
      )}
      <button type="submit" disabled={createCommunication.isPending}>
        {createCommunication.isPending ? "Adding..." : "Add Communication"}
      </button>
    </form>
  );
}
