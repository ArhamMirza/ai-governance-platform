import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApprovalWithdrawalNotice } from "../ApprovalWithdrawalNotice";

describe("ApprovalWithdrawalNotice", () => {
  it("warns that editing withdraws the approval once completed", () => {
    render(<ApprovalWithdrawalNotice status="completed" />);

    expect(screen.getByRole("status")).toHaveTextContent(/withdraws this approval/);
  });

  it("says nothing while there is no approval to lose", () => {
    for (const status of ["draft", "in_progress", "pending_owner_approval", "pending_caigo_approval"]) {
      const { container, unmount } = render(<ApprovalWithdrawalNotice status={status} />);
      expect(container).toBeEmptyDOMElement();
      unmount();
    }
  });
});
