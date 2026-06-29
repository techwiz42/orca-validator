"use client";

import { useEffect, useRef } from "react";

// Renders the verified machine's Mermaid source (from `orca compile mermaid`) client-side.
// `id` must be unique per diagram on the page (used as the mermaid render id).
export function MachineDiagram({ source, id = "m" }: { source: string | null; id?: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!source || !ref.current) return;
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "dark" });
        const { svg } = await mermaid.render(`mmd-${id}`, source);
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch {
        if (!cancelled && ref.current) ref.current.textContent = "diagram unavailable";
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source, id]);

  if (!source) return <p style={{ color: "#8b949e" }}>No diagram available.</p>;
  return <div ref={ref} style={{ overflowX: "auto" }} />;
}
