import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { RiskCriteriaEditor } from "../components/RiskCriteriaEditor";
import { useResetRiskCriteria, useRiskCriteria, useUpdateRiskCriteria } from "../hooks";

vi.mock("../hooks");

const criteria = {
  medium_min_score: 5,
  high_min_score: 13,
  is_default: true,
  min_score: 1,
  max_score: 25,
  updated_at: null,
};

function mockHooks({
  data = criteria,
  mutateAsync = vi.fn(),
  resetAsync = vi.fn(),
}: {
  data?: typeof criteria;
  mutateAsync?: ReturnType<typeof vi.fn>;
  resetAsync?: ReturnType<typeof vi.fn>;
} = {}) {
  vi.mocked(useRiskCriteria).mockReturnValue({
    data,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useUpdateRiskCriteria).mockReturnValue({ mutateAsync, isPending: false } as never);
  vi.mocked(useResetRiskCriteria).mockReturnValue({
    mutateAsync: resetAsync,
    isPending: false,
  } as never);
  return { mutateAsync, resetAsync };
}

describe("RiskCriteriaEditor", () => {
  it("renders the current bands as ranges", () => {
    mockHooks();

    render(<RiskCriteriaEditor />);

    expect(screen.getByText("1 – 4")).toBeInTheDocument();
    expect(screen.getByText("5 – 12")).toBeInTheDocument();
    expect(screen.getByText("13 – 25")).toBeInTheDocument();
  });

  it("badges the built-in defaults", () => {
    mockHooks();

    render(<RiskCriteriaEditor />);

    expect(screen.getByText("Using defaults")).toBeInTheDocument();
  });

  it("hides the default badge once criteria are customized", () => {
    mockHooks({ data: { ...criteria, high_min_score: 9, is_default: false } });

    render(<RiskCriteriaEditor />);

    expect(screen.queryByText("Using defaults")).not.toBeInTheDocument();
    expect(screen.getByText("9 – 25")).toBeInTheDocument();
  });

  it("saves edited bands", async () => {
    const { mutateAsync } = mockHooks();
    const user = userEvent.setup();

    render(<RiskCriteriaEditor />);
    await user.click(screen.getByRole("button", { name: "Edit" }));

    const highInput = screen.getByLabelText("High band starts at");
    await user.clear(highInput);
    await user.type(highInput, "9");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(mutateAsync).toHaveBeenCalledWith({ medium_min_score: 5, high_min_score: 9 });
  });

  it("surfaces the server's validation message", async () => {
    const mutateAsync = vi
      .fn()
      .mockRejectedValue(
        new ApiError(400, JSON.stringify({ detail: "medium_min_score must be lower than high_min_score" })),
      );
    mockHooks({ mutateAsync });
    const user = userEvent.setup();

    render(<RiskCriteriaEditor />);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "medium_min_score must be lower than high_min_score",
      );
    });
  });

  it("restores the defaults", async () => {
    const { resetAsync } = mockHooks();
    const user = userEvent.setup();

    render(<RiskCriteriaEditor />);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Restore defaults" }));

    expect(resetAsync).toHaveBeenCalled();
  });
});
