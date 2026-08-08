import { useEffect, useState } from "react";
import { fetchLeadDetail } from "../api/client";
import type { LeadDetail, StageResult } from "../types/lead";

interface LeadTraceProps {
  leadId: string | null;
}

const STAGE_LABELS: Record<StageResult["stage"], string> = {
  extract: "1 · Extract",
  classify: "2 · Classify",
  enrich: "3 · Enrich",
  route: "4 · Route",
};

const TERMINAL_STATUSES = new Set(["done", "failed"]);

export function LeadTrace({ leadId }: LeadTraceProps) {
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!leadId) {
      setDetail(null);
      return;
    }
    const id = leadId;
    let cancelled = false;
    let timer: number | undefined;
    setLoading(true);
    setError(null);

    async function poll() {
      try {
        const data = await fetchLeadDetail(id);
        if (cancelled) return;
        setDetail(data);
        setError(null);
        if (!TERMINAL_STATUSES.has(data.status)) {
          timer = window.setTimeout(() => void poll(), 1500);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load lead");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [leadId]);

  if (!leadId) {
    return (
      <section className="card">
        <h2>Trace</h2>
        <p className="hint">Select a lead from the table to inspect its pipeline trace.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Trace</h2>
      {loading && <p className="hint">Loading…</p>}
      {error && <p className="error">{error}</p>}
      {detail && (
        <div className="trace">
          <div className="trace-header">
            <div>
              <strong>{detail.raw_input.name || "(no name)"}</strong>
              {detail.raw_input.company && <span> · {detail.raw_input.company}</span>}
            </div>
            <span className={`badge badge-${detail.status}`}>{detail.status}</span>
          </div>
          {detail.error && <p className="error">{detail.error}</p>}
          {detail.stage_results.length === 0 && <p className="hint">No stages have run yet.</p>}
          <ol className="stage-list">
            {detail.stage_results.map((stage) => (
              <li key={stage.id} className={`stage-item ${stage.success ? "" : "stage-failed"}`}>
                <div className="stage-header">
                  <span className="stage-name">{STAGE_LABELS[stage.stage]}</span>
                  <span className="stage-meta">
                    {stage.prompt_version} · {stage.model} · {stage.latency_ms}ms
                    {!stage.success && " · FAILED"}
                  </span>
                </div>
                <details>
                  <summary>Input</summary>
                  <pre>{JSON.stringify(stage.input, null, 2)}</pre>
                </details>
                <details open>
                  <summary>Output</summary>
                  <pre>{JSON.stringify(stage.output, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
