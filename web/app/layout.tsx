import type { ReactNode } from "react";

import "./globals.css";

export const metadata = {
  title: "ORCA Validator",
  description: "ORCA-verified validation of business documents",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, -apple-system, sans-serif",
          margin: 0,
          background: "#0b0c10",
          color: "#e8e8e8",
        }}
      >
        {children}
        <footer
          style={{
            maxWidth: 820,
            margin: "24px auto 40px",
            padding: "16px 24px",
            borderTop: "1px solid #30363d",
            color: "#8b949e",
            fontSize: 13,
          }}
        >
          Experimental demo · documents are processed by a third-party AI (Together AI) — don&rsquo;t
          upload confidential material ·{" "}
          <a href="/privacy" style={{ color: "#58a6ff" }}>Privacy</a> ·{" "}
          <a href="/tos" style={{ color: "#58a6ff" }}>Terms</a>
          <div style={{ marginTop: 8 }}>
            Verdicts are formally verified by{" "}
            <a
              href="https://github.com/jascal/orca-lang"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#58a6ff" }}
            >
              ORCA · github.com/jascal/orca-lang
            </a>
          </div>
        </footer>
      </body>
    </html>
  );
}
