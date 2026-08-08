import { useEffect, useState } from "react";
import { fetchEvalRuns } from "../api/client";
import type { EvalRun } from "../types/lead";

export function EvalDashboard() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchEvalRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load eval runs");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="card">
      <h2>Eval results</h2>
      <p className="hint">
        Prompt-version-over-version accuracy on the hand-labeled classify eval set. Run{" "}
        <code>python -m app.evals.run_eval --prompt-version classify_v2</code> from{" "}
        <code>backend/</code> to add a new row.
      </p>
      {loading && <p className="hint">Loading…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && runs.length === 0 && (
        <p className="hint">No eval runs recorded yet.</p>
      )}
      {runs.length > 0 && (
        <div className="eval-bars">
          {runs.map((run) => (
            <div className="eval-bar-row" key={run.id}>
              <div className="eval-bar-label">
                <span>{run.prompt_version}</span>
                <span>
                  {run.passed_cases}/{run.total_cases} ({(run.pass_rate * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="eval-bar-track">
                <div className="eval-bar-fill" style={{ width: `${run.pass_rate * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
