import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { useFrameworkControls } from "../../framework-controls/hooks";
import type { FrameworkControl } from "../../framework-controls/types";
import { FrameworkTagPicker } from "../components/FrameworkTagPicker";
import { useFrameworkTags, useSetFrameworkTags, useSuggestFrameworkTags } from "../hooks";

vi.mock("../hooks");
vi.mock("../../framework-controls/hooks");

const controls: FrameworkControl[] = [
  { id: 1, framework: "iso_42001", code: "8.4", title: "AI system impact assessment", description: null, category: "clause" },
  { id: 2, framework: "iso_42001", code: "6.1", title: "Actions to address risks", description: null, category: "clause" },
  { id: 3, framework: "eu_ai_act", code: "Art.9", title: "Risk management system", description: null, category: "clause" },
];

function mockHooks({
  tags = [],
  mutateAsync = vi.fn(),
  suggestMutateAsync = vi.fn().mockResolvedValue([]),
}: {
  tags?: FrameworkControl[];
  mutateAsync?: ReturnType<typeof vi.fn>;
  suggestMutateAsync?: ReturnType<typeof vi.fn>;
} = {}) {
  vi.mocked(useFrameworkTags).mockReturnValue({
    data: tags,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useFrameworkControls).mockReturnValue({
    data: controls,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useSetFrameworkTags).mockReturnValue({ mutateAsync, isPending: false } as never);
  vi.mocked(useSuggestFrameworkTags).mockReturnValue({
    mutateAsync: suggestMutateAsync,
    isPending: false,
  } as never);
  return { mutateAsync, suggestMutateAsync };
}

describe("FrameworkTagPicker", () => {
  it("shows a placeholder when nothing is tagged", () => {
    mockHooks({ tags: [] });

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);

    expect(screen.getByText("No framework tags yet.")).toBeInTheDocument();
  });

  it("renders existing tags as chips", () => {
    mockHooks({ tags: [controls[0]] });

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);

    expect(screen.getByText("ISO 42001:8.4")).toBeInTheDocument();
  });

  it("groups available controls by framework when editing", async () => {
    mockHooks({ tags: [] });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));

    expect(screen.getByText("ISO 42001")).toBeInTheDocument();
    expect(screen.getByText("EU AI Act")).toBeInTheDocument();
    expect(screen.getByLabelText(/8\.4/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Art\.9/)).toBeInTheDocument();
  });

  it("pre-checks the entity's current tags when editing starts", async () => {
    mockHooks({ tags: [controls[0]] });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));

    expect(screen.getByLabelText(/8\.4/)).toBeChecked();
    expect(screen.getByLabelText(/6\.1/)).not.toBeChecked();
  });

  it("saves the selected control ids", async () => {
    const { mutateAsync } = mockHooks({ tags: [controls[0]] });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));
    await user.click(screen.getByLabelText(/Art\.9/));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(mutateAsync).toHaveBeenCalledWith(expect.arrayContaining([1, 3]));
    expect(mutateAsync.mock.calls[0][0]).toHaveLength(2);
  });

  it("discards changes on cancel", async () => {
    mockHooks({ tags: [controls[0]] });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));
    await user.click(screen.getByLabelText(/Art\.9/));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByText("ISO 42001:8.4")).toBeInTheDocument();
    expect(screen.queryByText("EU AI Act")).not.toBeInTheDocument();
  });

  it("pre-checks and labels the suggested controls", async () => {
    const { suggestMutateAsync } = mockHooks({
      tags: [],
      suggestMutateAsync: vi.fn().mockResolvedValue([controls[2]]),
    });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));
    await user.click(screen.getByRole("button", { name: "Suggest Tags" }));

    expect(suggestMutateAsync).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByLabelText(/Art\.9/)).toBeChecked();
    });
    expect(screen.getAllByText("Suggested")).toHaveLength(1);
  });

  it("layers a suggestion onto what's already picked, without unchecking it", async () => {
    mockHooks({
      tags: [controls[0]],
      suggestMutateAsync: vi.fn().mockResolvedValue([controls[2]]),
    });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));
    await user.click(screen.getByRole("button", { name: "Suggest Tags" }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Art\.9/)).toBeChecked();
    });
    expect(screen.getByLabelText(/8\.4/)).toBeChecked();
  });

  it("shows a plain message when nothing was similar enough to suggest", async () => {
    mockHooks({ tags: [], suggestMutateAsync: vi.fn().mockResolvedValue([]) });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));
    await user.click(screen.getByRole("button", { name: "Suggest Tags" }));

    await waitFor(() => {
      expect(
        screen.getByText(/Nothing in this record's text resembled a control/),
      ).toBeInTheDocument();
    });
  });

  it("surfaces an error if suggesting tags fails", async () => {
    mockHooks({
      tags: [],
      suggestMutateAsync: vi.fn().mockRejectedValue(new ApiError(503, "not available")),
    });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));
    await user.click(screen.getByRole("button", { name: "Suggest Tags" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("surfaces the server's validation message", async () => {
    const mutateAsync = vi
      .fn()
      .mockRejectedValue(new ApiError(400, JSON.stringify({ detail: "Unknown framework control id(s): [999]" })));
    mockHooks({ tags: [], mutateAsync });
    const user = userEvent.setup();

    render(<FrameworkTagPicker entityType="Policy" entityId={1} />);
    await user.click(screen.getByRole("button", { name: "Edit Tags" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Unknown framework control id(s)");
    });
  });
});
