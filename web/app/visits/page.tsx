"use client";

import { useEffect, useState } from "react";

type Visit = { ip: string; path: string; user_agent: string | null; hit_at: string | null };
type VisitsResponse = { total: number; unique_ips: number; showing: number; visits: Visit[] };

const KEY_STORAGE = "orca_admin_key";

export default function VisitsPage() {
  const [apiKey, setApiKey] = useState("");
  const [data, setData] = useState<VisitsResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem(KEY_STORAGE) : null;
    if (saved) setApiKey(saved);
  }, []);

  async function load() {
    if (!apiKey) return;
    setBusy(true);
    setError("");
    setData(null);
    try {
      const res = await fetch("/api/visits?limit=1000", {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.status === 401) {
        setError("Invalid API key.");
        return;
      }
      if (!res.ok) {
        setError(`Error ${res.status}`);
        return;
      }
      window.localStorage.setItem(KEY_STORAGE, apiKey);
      setData(await res.json());
    } catch {
      setError("Request failed.");
    } finally {
      setBusy(false);
    }
  }

  const cell: React.CSSProperties = {
    padding: "6px 10px",
    borderBottom: "1px solid #21262d",
    textAlign: "left",
    verticalAlign: "top",
  };
  const th: React.CSSProperties = { ...cell, color: "#8b949e", fontWeight: 600, position: "sticky", top: 0, background: "#0d1117" };

  return (
    <main style={{ maxWidth: 980, margin: "40px auto", padding: "0 24px" }}>
      <h1 style={{ marginBottom: 4 }}>Visit log</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        IP + time of every hit to the site. API-key protected — enter the key to view.
      </p>

      <div style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load()}
          placeholder="API key"
          style={{
            flex: 1,
            maxWidth: 360,
            background: "#0d1117",
            color: "#e8e8e8",
            border: "1px solid #30363d",
            borderRadius: 6,
            padding: "8px 10px",
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
          }}
        />
        <button
          onClick={load}
          disabled={!apiKey || busy}
          style={{
            padding: "8px 16px",
            background: busy ? "#21262d" : "#238636",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            cursor: apiKey && !busy ? "pointer" : "default",
          }}
        >
          {busy ? "Loading…" : "Load"}
        </button>
      </div>

      {error && <p style={{ color: "#f85149" }}>{error}</p>}

      {data && (
        <>
          <p style={{ color: "#8b949e" }}>
            <strong style={{ color: "#e8e8e8" }}>{data.total}</strong> total hits ·{" "}
            <strong style={{ color: "#e8e8e8" }}>{data.unique_ips}</strong> unique IPs · showing{" "}
            {data.showing} most recent
          </p>
          <div style={{ overflowX: "auto", maxHeight: "70vh", overflowY: "auto", border: "1px solid #30363d", borderRadius: 8 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={th}>Time (UTC)</th>
                  <th style={th}>IP</th>
                  <th style={th}>Path</th>
                  <th style={th}>User agent</th>
                </tr>
              </thead>
              <tbody>
                {data.visits.map((v, i) => (
                  <tr key={i}>
                    <td style={{ ...cell, whiteSpace: "nowrap", fontFamily: "ui-monospace, monospace" }}>
                      {v.hit_at ? v.hit_at.replace("T", " ").slice(0, 19) : "—"}
                    </td>
                    <td style={{ ...cell, fontFamily: "ui-monospace, monospace", color: "#58a6ff" }}>{v.ip}</td>
                    <td style={{ ...cell, fontFamily: "ui-monospace, monospace" }}>{v.path}</td>
                    <td style={{ ...cell, color: "#8b949e" }}>{(v.user_agent || "").slice(0, 80)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
