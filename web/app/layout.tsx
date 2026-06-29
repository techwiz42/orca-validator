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
      </body>
    </html>
  );
}
