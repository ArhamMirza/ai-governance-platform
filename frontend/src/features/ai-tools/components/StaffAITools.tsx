import { useStaffAITools } from "../hooks";
import { classificationLabel } from "../labels";

/** The AI tools an employee may use, and the rules that go with each. */
export function StaffAITools() {
  const { data: tools, isLoading, isError } = useStaffAITools();

  if (isLoading) return <p>Loading approved tools...</p>;
  if (isError) return <p>Failed to load the approved tools.</p>;
  if (!tools || tools.length === 0) {
    return <p>No AI tools have been approved yet. You can ask for one below.</p>;
  }

  return (
    <ul className="plain-list">
      {tools.map((tool) => (
        <li key={tool.id} className="reporter-concern">
          <p>
            <strong>{tool.name}</strong>
            {tool.vendor && <span className="approval-note"> {tool.vendor}</span>}
          </p>
          <p>
            {tool.domains.join(", ")} · up to{" "}
            <strong>{classificationLabel(tool.max_data_classification).toLowerCase()}</strong> data
            {tool.status === "restricted" && " · limited use"}
          </p>
          {tool.conditions_of_use && <blockquote>{tool.conditions_of_use}</blockquote>}
        </li>
      ))}
    </ul>
  );
}
