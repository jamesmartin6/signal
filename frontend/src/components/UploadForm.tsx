import { useRef, useState, type FormEvent } from "react";
import { uploadLeadsCsv } from "../api/client";
import type { UploadResponse } from "../types/lead";

interface UploadFormProps {
  onUploaded: () => void;
}

export function UploadForm({ onUploaded }: UploadFormProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;

    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await uploadLeadsCsv(file);
      setResult(response);
      onUploaded();
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Upload leads</h2>
      <form onSubmit={handleSubmit} className="upload-form">
        <input ref={fileInputRef} type="file" accept=".csv,text/csv" required />
        <button type="submit" disabled={busy}>
          {busy ? "Uploading…" : "Upload CSV"}
        </button>
      </form>
      <p className="hint">
        Expected columns: <code>name</code>, <code>company</code>, <code>bio_or_linkedin_url</code>
      </p>
      {error && <p className="error">{error}</p>}
      {result && (
        <p className="result">
          Created {result.created} lead{result.created === 1 ? "" : "s"}
          {result.skipped > 0 && (
            <>
              {" "}
              · skipped {result.skipped} row{result.skipped === 1 ? "" : "s"}
            </>
          )}
        </p>
      )}
      {result && result.skipped_rows.length > 0 && (
        <ul className="skipped-rows">
          {result.skipped_rows.map((row) => (
            <li key={row.row_number}>
              Row {row.row_number}: {row.reason}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
