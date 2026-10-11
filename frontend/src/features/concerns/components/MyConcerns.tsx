import { useState } from "react";

import { readError } from "../../../shared/api/readError";
import { useLookupConcern, useMyConcerns } from "../hooks";
import { ReporterConcernCard } from "./ReporterConcernCard";

/** Follow up on a concern with its tracking code -- how someone who raised one
 * anonymously gets back to it. */
function LookupByCode() {
  const lookup = useLookupConcern();
  const [code, setCode] = useState("");

  return (
    <section>
      <h2>Look up a concern by its tracking code</h2>
      <p className="approval-note">
        For a concern you raised anonymously. Spaces and dashes don't matter.
      </p>
      <div className="inline-form">
        <label htmlFor="tracking-code">Tracking code</label>
        <input
          id="tracking-code"
          value={code}
          autoComplete="off"
          onChange={(e) => setCode(e.target.value)}
        />
        <button onClick={() => lookup.mutate(code)} disabled={!code.trim() || lookup.isPending}>
          {lookup.isPending ? "Looking..." : "Look up"}
        </button>
      </div>
      {lookup.isError && (
        <p role="alert">
          {readError(lookup.error, "That code didn't match a concern. Check it and try again.")}
        </p>
      )}
      {lookup.data && <ReporterConcernCard concern={lookup.data} />}
    </section>
  );
}

/** The concerns this person raised under their own name, and the lookup for
 * anonymous ones. */
export function MyConcerns() {
  const { data: concerns, isLoading, isError } = useMyConcerns();

  return (
    <div>
      <section>
        <h2>Concerns you raised under your name</h2>
        {isLoading ? (
          <p>Loading your concerns...</p>
        ) : isError ? (
          <p>Failed to load your concerns.</p>
        ) : !concerns || concerns.length === 0 ? (
          <p>You haven't raised any concerns under your name.</p>
        ) : (
          concerns.map((concern) => <ReporterConcernCard key={concern.id} concern={concern} />)
        )}
      </section>
      <LookupByCode />
    </div>
  );
}
