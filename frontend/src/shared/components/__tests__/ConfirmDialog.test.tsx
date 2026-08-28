import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "../ConfirmDialog";

describe("ConfirmDialog", () => {
  it("shows the title and what will happen", () => {
    render(
      <ConfirmDialog
        title="Delete this AI system?"
        message="Its assessments go too."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getByText("Delete this AI system?")).toBeInTheDocument();
    expect(screen.getByText("Its assessments go too.")).toBeInTheDocument();
  });

  it("confirms only when the confirm button is pressed", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const user = userEvent.setup();

    render(
      <ConfirmDialog
        title="Delete?"
        message="Gone for good."
        confirmLabel="Delete it"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete it" }));
    expect(onConfirm).toHaveBeenCalled();
  });

  it("disables both actions while the delete is in flight", () => {
    render(
      <ConfirmDialog
        title="Delete?"
        message="Gone for good."
        isPending
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Deleting..." })).toBeDisabled();
  });

  it("surfaces a failure without closing", () => {
    render(
      <ConfirmDialog
        title="Delete?"
        message="Gone for good."
        error="Something went wrong"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong");
  });
});
