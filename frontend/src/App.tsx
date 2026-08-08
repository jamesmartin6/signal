import { useState } from "react";
import { EvalDashboard } from "./components/EvalDashboard";
import { LeadsTable } from "./components/LeadsTable";
import { LeadTrace } from "./components/LeadTrace";
import { UploadForm } from "./components/UploadForm";
import { useLeadsPolling } from "./hooks/useLeadsPolling";

export default function App() {
  const { leads, error, loading, anyInFlight, refetch } = useLeadsPolling();
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Signal</h1>
        <p className="tagline">AI-powered lead enrichment &amp; routing pipeline</p>
      </header>

      <main className="app-main">
        <div className="app-top">
          <UploadForm onUploaded={refetch} />
        </div>

        <div className="app-columns">
          <section className="card">
            <h2>Leads</h2>
            <LeadsTable
              leads={leads}
              loading={loading}
              error={error}
              anyInFlight={anyInFlight}
              selectedLeadId={selectedLeadId}
              onSelectLead={setSelectedLeadId}
            />
          </section>
          <LeadTrace leadId={selectedLeadId} />
        </div>

        <EvalDashboard />
      </main>
    </div>
  );
}
