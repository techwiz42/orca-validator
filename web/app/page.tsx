"use client";

import { useEffect, useState } from "react";

import { MachineDiagram } from "./MachineDiagram";

type Result = {
  ready: boolean;
  status: string;
  verdict?: string;
  final_state?: string;
  reasons?: string[];
  extracted_fields?: Record<string, boolean>;
  machine_id?: string;
  machine_hash?: string;
};

const PANEL: React.CSSProperties = {
  border: "1px solid #30363d",
  borderRadius: 8,
  padding: 24,
  marginBottom: 24,
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [mermaidSrc, setMermaidSrc] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/machines/contract_validation")
      .then((r) => r.json())
      .then((d) => setMermaidSrc(d.mermaid ?? null))
      .catch(() => setMermaidSrc(null));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setResult(null);
    setStatus("uploading…");

    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", "contract");

    const res = await fetch("/api/documents", { method: "POST", body: form });
    if (!res.ok) {
      setStatus("upload failed");
      setBusy(false);
      return;
    }
    const { document_id } = await res.json();

    for (let i = 0; i < 60; i++) {
      const r: Result = await fetch(`/api/documents/${document_id}/result`).then((x) => x.json());
      setStatus(r.status);
      if (r.ready) {
        setResult(r);
        break;
      }
      await new Promise((done) => setTimeout(done, 1000));
    }
    setBusy(false);
  }

  const verdictColor =
    result?.verdict === "pass" ? "#3fb950" : result?.verdict === "fail" ? "#f85149" : "#8b949e";

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 4 }}>ORCA Validator</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Upload a contract PDF. It is validated by a <strong>formally-verified</strong> ORCA state
        machine — the rules are the machine, and its topology was checked before it ran.
      </p>

      <form onSubmit={onSubmit} style={{ ...PANEL, borderStyle: "dashed" }}>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          type="submit"
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
        {status && <span style={{ marginLeft: 12, color: "#8b949e" }}>status: {status}</span>}
      </form>

      {result && (
        <section style={PANEL}>
          <h2 style={{ color: verdictColor, marginTop: 0 }}>
            Verdict: {result.verdict?.toUpperCase()}
          </h2>
          <p>
            Final state: <code>{result.final_state}</code>
          </p>
          {result.reasons && result.reasons.length > 0 && (
            <>
              <p>Reasons:</p>
              <ul>
                {result.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </>
          )}
          {result.extracted_fields && (
            <>
              <p>Required fields:</p>
              <ul>
                {Object.entries(result.extracted_fields).map(([k, v]) => (
                  <li key={k} style={{ color: v ? "#3fb950" : "#f85149" }}>
                    {k}: {v ? "✓ present" : "✗ missing"}
                  </li>
                ))}
              </ul>
            </>
          )}
          <p style={{ color: "#8b949e", fontSize: 12 }}>
            verified machine <code>{result.machine_id}</code> ({result.machine_hash?.slice(0, 12)})
          </p>
        </section>
      )}

      <section style={PANEL}>
        <h3 style={{ marginTop: 0 }}>Validation machine — verified topology</h3>
        <MachineDiagram source={mermaidSrc} />
      </section>
    </main>
  );
}
