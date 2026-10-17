import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { readError } from "../../../shared/api/readError";
import { useRequestAITool, useRequestableAITools } from "../hooks";

/** The picker's value for a tool that isn't in the list. */
const SOMETHING_ELSE = "";

const requestSchema = z
  .object({
    tool: z.string(),
    tool_name: z.string(),
    domain: z.string(),
    purpose: z.string().trim().min(10, "Tell us a little more about what you'd use it for"),
    data_involved: z.string(),
  })
  .refine((values) => values.tool !== SOMETHING_ELSE || values.tool_name.trim().length > 0, {
    message: "What is the tool called?",
    path: ["tool_name"],
  });

type RequestValues = z.infer<typeof requestSchema>;

interface RequestAIToolFormProps {
  /** What to start the form with, e.g. from the link on the browser extension's
   * "not approved" page. A name matching a known tool selects it. */
  initial?: { name?: string; domain?: string };
  /** Called with the tool's name once the request has been sent. */
  onRequested?: (toolName: string) => void;
}

/** An employee asks for an AI tool to be allowed. The Chief AI Governance
 * Officer decides; the answer shows under their requests. */
export function RequestAIToolForm({ initial, onRequested }: RequestAIToolFormProps) {
  const { data: known } = useRequestableAITools();
  const request = useRequestAITool();
  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<RequestValues>({
    resolver: zodResolver(requestSchema),
    defaultValues: {
      tool: SOMETHING_ELSE,
      tool_name: initial?.name ?? "",
      domain: initial?.domain ?? "",
      purpose: "",
      data_involved: "",
    },
  });
  const initialName = initial?.name;

  // The list of known tools arrives after the form does; once it has, a tool
  // the link named is selected rather than typed in again.
  useEffect(() => {
    if (!initialName || !known) return;
    const match = known.find((tool) => tool.name.toLowerCase() === initialName.toLowerCase());
    if (match) setValue("tool", String(match.id));
  }, [initialName, known, setValue]);
  const picked = watch("tool") !== SOMETHING_ELSE;

  const onSubmit = handleSubmit((values) => {
    const chosen = known?.find((tool) => String(tool.id) === values.tool);
    const toolName = chosen ? chosen.name : values.tool_name.trim();
    // The error shows from request.error; nothing here needs to catch it.
    request.mutate(
      {
        tool_id: chosen ? chosen.id : null,
        tool_name: toolName,
        // A known tool already has its address; only a new one needs it.
        domain: chosen ? null : values.domain.trim() || null,
        purpose: values.purpose.trim(),
        data_involved: values.data_involved.trim() || null,
      },
      {
        onSuccess: () => {
          reset();
          onRequested?.(toolName);
        },
      },
    );
  });

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="request-tool">Which tool?</label>
        <select id="request-tool" {...register("tool")}>
          <option value={SOMETHING_ELSE}>Something else -- I'll type it</option>
          {(known ?? []).map((tool) => (
            <option key={tool.id} value={tool.id}>
              {tool.name}
              {tool.vendor ? ` (${tool.vendor})` : ""}
            </option>
          ))}
        </select>
      </div>
      {!picked && (
        <>
          <div>
            <label htmlFor="request-tool-name">Name of the tool</label>
            <input id="request-tool-name" {...register("tool_name")} />
            {errors.tool_name && <p role="alert">{errors.tool_name.message}</p>}
          </div>
          <div>
            <label htmlFor="request-domain">Its website, if you know it</label>
            <input id="request-domain" placeholder="example.com" {...register("domain")} />
          </div>
        </>
      )}
      <div>
        <label htmlFor="request-purpose">What would you use it for?</label>
        <textarea id="request-purpose" {...register("purpose")} />
        {errors.purpose && <p role="alert">{errors.purpose.message}</p>}
      </div>
      <div>
        <label htmlFor="request-data">What kind of information would you put into it?</label>
        <textarea id="request-data" {...register("data_involved")} />
      </div>
      {request.isError && (
        <p role="alert">{readError(request.error, "Your request could not be sent.")}</p>
      )}
      <button type="submit" disabled={request.isPending}>
        {request.isPending ? "Sending..." : "Send request"}
      </button>
    </form>
  );
}
