import { useState } from "react";

import { ClauseMappingTable } from "../features/framework-mapping/components/ClauseMappingTable";
import { SoaTable } from "../features/framework-soa/components/SoaTable";

type Tab = "mapping" | "soa";

export function FrameworksPage() {
  const [tab, setTab] = useState<Tab>("mapping");

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
          className={tab === "mapping" ? "active" : undefined}
          onClick={() => setTab("mapping")}
        >
          Clause Mapping
        </button>
        <button className={tab === "soa" ? "active" : undefined} onClick={() => setTab("soa")}>
          Statement of Applicability
        </button>
      </div>

      {tab === "mapping" ? <ClauseMappingTable /> : <SoaTable />}
    </section>
  );
}
