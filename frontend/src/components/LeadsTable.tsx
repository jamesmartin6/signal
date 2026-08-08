import type { Lead, LeadStatus } from "../types/lead";

const STATUS_LABELS: Record<LeadStatus, string> = {
  pending: "Pending",
  extracting: "Extracting",
  classifying: "Classifying",
  enriching: "Enriching",
  routing: "Routing",
  done: "Done",
  failed: "Failed",
};

interface LeadsTableProps {
  leads: Lead[];
  loading: boolean;
  error: string | null;
  anyInFlight: boolean;
  selectedLeadId: string | null;
  onSelectLead: (id: string) => void;
}

export function LeadsTable({ leads, loading, error, anyInFlight, selectedLeadId, onSelectLead }: LeadsTableProps) {
  if (loading) return <p className="hint">Loading leads…</p>;
  if (error) return <p className="error">{error}</p>;
  if (leads.length === 0) return <p className="hint">No leads yet — upload a CSV to get started.</p>;

  return (
    <div>
      <table className="leads-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Company</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr
              key={lead.id}
              className={lead.id === selectedLeadId ? "selected" : ""}
              onClick={() => onSelectLead(lead.id)}
            >
              <td>{lead.raw_input.name || "—"}</td>
              <td>{lead.raw_input.company || "—"}</td>
              <td>
                <StatusBadge status={lead.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {anyInFlight && <p className="hint polling-hint">Pipeline running… refreshing every 1.5s</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: LeadStatus }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status]}</span>;
}
