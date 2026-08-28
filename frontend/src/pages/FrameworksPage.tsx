import { useState } from "react";

import { ClauseMappingTable } from "../features/framework-mapping/components/ClauseMappingTable";
import { SoaTable } from "../features/framework-soa/components/SoaTable";

type Tab = "iso-clauses" | "iso-soa" | "eu-ai-act";

export function FrameworksPage() {
  const [tab, setTab] = useState<Tab>("iso-clauses");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Frameworks</h1>
          <p>See which policies, procedures, risk assessments, and evidence are tagged against each clause or control.</p>
        </div>
      </div>

      <div className="tab-bar">
        <button
          className={tab === "iso-clauses" ? "active" : undefined}
          onClick={() => setTab("iso-clauses")}
        >
          ISO 42001 Clauses
        </button>
        <button
          className={tab === "iso-soa" ? "active" : undefined}
          onClick={() => setTab("iso-soa")}
        >
          ISO 42001 Statement of Applicability
        </button>
        <button
          className={tab === "eu-ai-act" ? "active" : undefined}
          onClick={() => setTab("eu-ai-act")}
        >
          EU AI Act
        </button>
      </div>

      {tab === "iso-clauses" && <ClauseMappingTable framework="iso_42001" />}
      {tab === "iso-soa" && <SoaTable />}
      {tab === "eu-ai-act" && <ClauseMappingTable framework="eu_ai_act" />}
    </section>
  );
}
