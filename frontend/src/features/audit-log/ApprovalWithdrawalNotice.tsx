/** Editing an approved assessment withdraws the CAIGO sign-off and sends it
 * back to draft (approval_chain_service.revert_to_draft). Warn before someone
 * edits rather than surprising them after. Renders nothing unless the record
 * actually holds an approval worth losing. */
export function ApprovalWithdrawalNotice({ status }: { status: string }) {
  if (status !== "completed") return null;

  return (
    <p className="approval-withdrawal-notice" role="status">
      <strong>Approved.</strong>
      <span>
        Changing what was assessed &mdash; scores, risk items or the write-up &mdash;
        withdraws this approval and returns it to draft for re-approval. Recording
        treatment progress on a risk item does not.
      </span>
    </p>
  );
}
