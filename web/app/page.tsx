"use client";

import { useEffect, useRef, useState } from "react";

import { MachineDiagram } from "./MachineDiagram";

type Issue = { severity?: string; issue?: string; recommendation?: string };
type Analysis = {
  summary?: string;
  aims?: string;
  parties?: string[];
  key_terms?: { term?: string; detail?: string }[];
  strengths?: string[];
  weaknesses?: string[];
  potential_pitfalls?: string[];
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
  revised_redline?: string;
  document_fsm?: { mermaid?: string | null; verified?: boolean; report?: string };
};

// Render {--removed--}/{++added++} markup as red (struck) / green spans. React escapes the
// text, so this is XSS-safe even though the content is model-generated.
function renderRedline(text: string) {
  return text.split(/(\{--[\s\S]*?--\}|\{\+\+[\s\S]*?\+\+\})/).map((p, i) => {
    const del = p.match(/^\{--([\s\S]*)--\}$/);
    if (del) {
      return (
        <del key={i} style={{ color: "#f85149", background: "#3d1417", textDecoration: "line-through" }}>
          {del[1]}
        </del>
      );
    }
    const ins = p.match(/^\{\+\+([\s\S]*)\+\+\}$/);
    if (ins) {
      return (
        <ins key={i} style={{ color: "#3fb950", background: "#0f2417", textDecoration: "none" }}>
          {ins[1]}
        </ins>
      );
    }
    // plain segment — strip any stray/unbalanced markers the model may have left
    return <span key={i}>{p.replace(/\{--|--\}|\{\+\+|\+\+\}/g, "")}</span>;
  });
}

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
  const [pasteText, setPasteText] = useState("");
  const [temperature, setTemperature] = useState(0.03);
  const runToken = useRef(0);  // invalidates a prior analysis's polling loop when a new one starts

  async function validate(f: File) {
    // Begin a fresh analysis: bump the token (invalidates any in-flight prior loop) and wipe old data.
    const myToken = ++runToken.current;
    setBusy(true);
    setResult(null);
    setDocId(null);
    setStatus("uploading…");
    const form = new FormData();
    form.append("file", f);
    form.append("doc_type", "contract");
    form.append("temperature", String(temperature));
    const res = await fetch("/api/documents", { method: "POST", body: form });
    if (runToken.current !== myToken) return;  // superseded by a newer analysis
    if (!res.ok) {
      setStatus("upload failed");
      setBusy(false);
      return;
    }
    const { document_id } = await res.json();
    if (runToken.current !== myToken) return;
    setDocId(document_id);
    const start = Date.now();
    for (let i = 0; i < 240; i++) {
      const r: Result = await fetch(`/api/documents/${document_id}/result`).then((x) => x.json());
      if (runToken.current !== myToken) return;  // a newer analysis started — never write stale data
      if (r.ready) {
        setResult(r);
        setStatus("done");
        break;
      }
      const secs = Math.round((Date.now() - start) / 1000);
      setStatus(`analyzing… ${secs}s — long documents can take a few minutes`);
      await new Promise((done) => setTimeout(done, 1500));
    }
    if (runToken.current === myToken) setBusy(false);
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
        {status && (
          <div style={{ marginTop: 12, color: "#8b949e", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            {busy && <span className="spinner" aria-label="processing" />}
            <span>{status}</span>
          </div>
        )}
      </div>

      <div style={PANEL}>
        <label style={{ display: "flex", alignItems: "center", gap: 12, color: "#8b949e", fontSize: 14 }}>
          <span style={{ whiteSpace: "nowrap" }}>LLM temperature</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            disabled={busy}
            style={{ flex: 1 }}
          />
          <span style={{ width: 44, textAlign: "right", color: "#e8e8e8", fontVariantNumeric: "tabular-nums" }}>
            {temperature.toFixed(2)}
          </span>
        </label>
        <p style={{ margin: "8px 0 0", color: "#6e7681", fontSize: 12 }}>
          Lower = more deterministic &amp; consistent; higher = more varied. Applies to the analysis,
          revision, and state-machine extraction. Structured outputs (the analysis JSON and the
          extracted machine) can degrade at very high values.
        </p>
      </div>

      <div style={PANEL}>
        <p style={{ marginTop: 0, color: "#8b949e" }}>…or paste text directly:</p>
        <textarea
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder="Paste contract or document text here…"
          rows={5}
          style={{
            width: "100%",
            boxSizing: "border-box",
            background: "#0d1117",
            color: "#e8e8e8",
            border: "1px solid #30363d",
            borderRadius: 6,
            padding: 10,
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
            fontSize: 13,
          }}
        />
        <button
          onClick={() =>
            pasteText.trim() &&
            validate(new File([pasteText], "pasted.txt", { type: "text/plain" }))
          }
          disabled={!pasteText.trim() || busy}
          style={{
            marginTop: 8,
            padding: "6px 14px",
            background: busy ? "#21262d" : "#238636",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            cursor: pasteText.trim() && !busy ? "pointer" : "default",
          }}
        >
          Validate pasted text
        </button>
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

          {result.analysis_status === "done" && a && (
            <section style={PANEL}>
              <h3 style={{ marginTop: 0 }}>
                Assessment <span style={{ color: "#8b949e", fontSize: 12 }}>(AI-assisted)</span>
              </h3>
              {a.summary && <p>{a.summary}</p>}
              {a.aims && (
                <p><strong>Aims:</strong> {a.aims}</p>
              )}
              {a.strengths && a.strengths.length > 0 && (
                <>
                  <p style={{ color: "#3fb950", marginBottom: 4 }}><strong>Strengths</strong></p>
                  <ul>{a.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </>
              )}
              {a.weaknesses && a.weaknesses.length > 0 && (
                <>
                  <p style={{ color: "#d29922", marginBottom: 4 }}><strong>Weaknesses</strong></p>
                  <ul>{a.weaknesses.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </>
              )}
              {a.potential_pitfalls && a.potential_pitfalls.length > 0 && (
                <>
                  <p style={{ color: "#f85149", marginBottom: 4 }}><strong>Potential pitfalls</strong></p>
                  <ul>{a.potential_pitfalls.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </>
              )}
            </section>
          )}

          {result.document_fsm && (result.document_fsm.mermaid || result.document_fsm.report) && (
            <section style={PANEL}>
              <h3 style={{ marginTop: 0 }}>
                Document state machine{" "}
                <span style={{ color: "#8b949e", fontSize: 12 }}>(extracted + ORCA-verified)</span>
              </h3>
              <p style={{ color: "#8b949e", fontSize: 13, marginTop: 0 }}>
                The lifecycle / process <em>this document describes</em>, extracted as a state machine
                and run through the ORCA verifier.
              </p>
              <p>
                {result.document_fsm.verified ? (
                  <span style={{ color: "#3fb950" }}>
                    ✓ Formally verified — reachable, deadlock-free, complete.
                  </span>
                ) : (
                  <span style={{ color: "#d29922" }}>
                    ⚠ The verifier flagged issues below — a possible gap in the document&rsquo;s own logic.
                  </span>
                )}
              </p>
              {result.document_fsm.mermaid && (
                <MachineDiagram source={result.document_fsm.mermaid} id="docfsm" />
              )}
              {!result.document_fsm.verified && result.document_fsm.report && (
                <pre style={{
                  whiteSpace: "pre-wrap", color: "#8b949e", fontSize: 12, background: "#0d1117",
                  border: "1px solid #30363d", borderRadius: 6, padding: 12, marginTop: 8,
                }}>
                  {result.document_fsm.report}
                </pre>
              )}
            </section>
          )}

          {result.revised_available && docId && (
            <section style={PANEL}>
              <h3 style={{ marginTop: 0 }}>
                Proposed revised document{" "}
                <span style={{ color: "#8b949e", fontSize: 12 }}>(AI-assisted redline)</span>
              </h3>
              {result.revised_redline && (
                <div
                  style={{
                    whiteSpace: "pre-wrap",
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    fontSize: 13,
                    lineHeight: 1.7,
                    background: "#0d1117",
                    border: "1px solid #30363d",
                    borderRadius: 6,
                    padding: 16,
                    maxHeight: 480,
                    overflowY: "auto",
                  }}
                >
                  {renderRedline(result.revised_redline)}
                </div>
              )}
              <p style={{ marginTop: 12 }}>
                <a href={`/api/documents/${docId}/revised?format=docx`}
                   style={{ color: "#58a6ff", marginRight: 16 }}>⬇ Download .docx</a>
                <a href={`/api/documents/${docId}/revised?format=md`}
                   style={{ color: "#58a6ff" }}>⬇ Download .md</a>
              </p>
              <p style={{ color: "#8b949e", fontSize: 12, marginBottom: 0 }}>
                <span style={{ color: "#3fb950" }}>green</span> = added ·{" "}
                <span style={{ color: "#f85149" }}>red</span> = removed · downloads contain the
                accepted (clean) version.
              </p>
            </section>
          )}
        </>
      )}

    </main>
  );
}
