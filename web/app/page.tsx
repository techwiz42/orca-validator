"use client";

import { useEffect, useState } from "react";

import { MachineDiagram } from "./MachineDiagram";

type Issue = { severity?: string; issue?: string; recommendation?: string };
type Analysis = {
  summary?: string;
  parties?: string[];
  key_terms?: { term?: string; detail?: string }[];
  issues?: Issue[];
  missing_or_weak_clauses?: string[];
  overall_recommendation?: string;
  error?: string;
};
type Result = {
  ready: boolean;
  status: string;
  verdict?: string;
  final_state?: string;
  reasons?: string[];
  extracted_fields?: Record<string, boolean>;
  machine_id?: string;
  machine_hash?: string;
  analysis?: Analysis;
  analysis_status?: string;
  revised_available?: boolean;
};

const PANEL: React.CSSProperties = {
  border: "1px solid #30363d",
  borderRadius: 8,
  padding: 24,
  marginBottom: 24,
};
const sevColor = (s?: string) =>
  s === "high" ? "#f85149" : s === "medium" ? "#d29922" : "#3fb950";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [mermaidSrc, setMermaidSrc] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/machines/contract_validation")
      .then((r) => r.json())
      .then((d) => setMermaidSrc(d.mermaid ?? null))
      .catch(() => setMermaidSrc(null));
  }, []);

  async function validate(f: File) {
    setBusy(true);
    setResult(null);
    setDocId(null);
    setStatus("uploading…");
    const form = new FormData();
    form.append("file", f);
    form.append("doc_type", "contract");
    const res = await fetch("/api/documents", { method: "POST", body: form });
    if (!res.ok) {
      setStatus("upload failed");
      setBusy(false);
      return;
    }
    const { document_id } = await res.json();
    setDocId(document_id);
    for (let i = 0; i < 120; i++) {
      const r: Result = await fetch(`/api/documents/${document_id}/result`).then((x) => x.json());
      setStatus(r.status + (r.ready ? "" : " — analyzing…"));
      if (r.ready) {
        setResult(r);
        break;
      }
      await new Promise((done) => setTimeout(done, 1500));
    }
    setBusy(false);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
      validate(f);
    }
  }

  const verdictColor =
    result?.verdict === "pass" ? "#3fb950" : result?.verdict === "fail" ? "#f85149" : "#8b949e";
  const a = result?.analysis;

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 4 }}>ORCA Validator</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Upload a document — PDF, image, Word, or text. The verdict is from a{" "}
        <strong>formally-verified</strong> ORCA state machine, <strong>tuned for contracts</strong>;
        the analysis and proposed revision are AI-assisted.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          ...PANEL,
          borderStyle: "dashed",
          borderColor: dragging ? "#3fb950" : "#30363d",
          background: dragging ? "#0f1a12" : "transparent",
          textAlign: "center",
        }}
      >
        <p style={{ marginTop: 0, color: "#8b949e" }}>
          Drag &amp; drop a document here, or choose one:
        </p>
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.gif,.webp,.docx,.txt,.md,application/pdf,image/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          onClick={() => file && validate(file)}
          disabled={!file || busy}
          style={{
            marginLeft: 12,
            padding: "6px 14px",
            background: busy ? "#21262d" : "#238636",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            cursor: file && !busy ? "pointer" : "default",
          }}
        >
          {busy ? "Validating…" : "Validate"}
        </button>
        {status && <div style={{ marginTop: 10, color: "#8b949e" }}>status: {status}</div>}
      </div>

      {result && (
        <>
          <section style={PANEL}>
            <h2 style={{ color: verdictColor, marginTop: 0 }}>
              Verdict: {result.verdict?.toUpperCase()}
            </h2>
            <p style={{ color: "#8b949e", fontSize: 13 }}>
              Machine-verified structural verdict (state <code>{result.final_state}</code>) ·
              verified machine <code>{result.machine_id}</code> ({result.machine_hash?.slice(0, 12)})
            </p>
            {result.reasons && result.reasons.length > 0 && (
              <ul>{result.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
            )}
            {result.extracted_fields && (
              <ul style={{ columns: 2 }}>
                {Object.entries(result.extracted_fields).map(([k, v]) => (
                  <li key={k} style={{ color: v ? "#3fb950" : "#f85149" }}>
                    {k}: {v ? "✓" : "✗ missing"}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section style={PANEL}>
            <h3 style={{ marginTop: 0 }}>
              Analysis <span style={{ color: "#8b949e", fontSize: 12 }}>(AI-assisted)</span>
            </h3>
            {result.analysis_status === "skipped" && (
              <p style={{ color: "#8b949e" }}>
                AI analysis is not configured on this deployment (set <code>TOGETHER_API_KEY</code>).
              </p>
            )}
            {result.analysis_status === "error" && (
              <p style={{ color: "#f85149" }}>Analysis failed: {a?.error}</p>
            )}
            {result.analysis_status === "done" && a && (
              <>
                {a.summary && <p>{a.summary}</p>}
                {a.parties && a.parties.length > 0 && (
                  <p><strong>Parties:</strong> {a.parties.join(", ")}</p>
                )}
                {a.issues && a.issues.length > 0 && (
                  <>
                    <p><strong>Issues</strong></p>
                    <ul>
                      {a.issues.map((it, i) => (
                        <li key={i} style={{ marginBottom: 6 }}>
                          <span style={{ color: sevColor(it.severity), fontWeight: 600 }}>
                            [{(it.severity || "—").toUpperCase()}]
                          </span>{" "}
                          {it.issue}
                          {it.recommendation && (
                            <div style={{ color: "#8b949e", fontSize: 13 }}>↳ {it.recommendation}</div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {a.missing_or_weak_clauses && a.missing_or_weak_clauses.length > 0 && (
                  <>
                    <p><strong>Missing / weak clauses</strong></p>
                    <ul>{a.missing_or_weak_clauses.map((c, i) => <li key={i}>{c}</li>)}</ul>
                  </>
                )}
                {a.overall_recommendation && (
                  <p><strong>Overall:</strong> {a.overall_recommendation}</p>
                )}
              </>
            )}
          </section>

          {result.revised_available && docId && (
            <section style={PANEL}>
              <h3 style={{ marginTop: 0 }}>
                Proposed revised document <span style={{ color: "#8b949e", fontSize: 12 }}>(AI-assisted)</span>
              </h3>
              <p>
                <a href={`/api/documents/${docId}/revised?format=docx`}
                   style={{ color: "#58a6ff", marginRight: 16 }}>⬇ Download .docx</a>
                <a href={`/api/documents/${docId}/revised?format=md`}
                   style={{ color: "#58a6ff" }}>⬇ Download .md</a>
              </p>
            </section>
          )}
        </>
      )}

      <section style={PANEL}>
        <h3 style={{ marginTop: 0 }}>Validation machine — verified topology</h3>
        <MachineDiagram source={mermaidSrc} />
      </section>
    </main>
  );
}
