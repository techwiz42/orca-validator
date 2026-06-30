import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { backendFetch } from "@/lib/backend";

// Records every page hit (IP + time) to the backend visit log. nginx forwards the real client IP
// via X-Forwarded-For / X-Real-IP. Fire-and-forget — a logging failure never blocks the page.
export function middleware(req: NextRequest) {
  const xff = req.headers.get("x-forwarded-for") || "";
  const ip = (xff.split(",")[0] || req.headers.get("x-real-ip") || "unknown").trim() || "unknown";
  void backendFetch("/visits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ip,
      path: req.nextUrl.pathname,
      user_agent: req.headers.get("user-agent") || "",
    }),
  }).catch(() => {});
  return NextResponse.next();
}

// Run on page navigations only — skip Next internals, the API proxy, and the favicon.
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
