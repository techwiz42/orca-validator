import type { ReactNode } from "react";

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
        </footer>
      </body>
    </html>
  );
}
