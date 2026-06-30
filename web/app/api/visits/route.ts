import { NextRequest, NextResponse } from "next/server";

// Forwards the CALLER's Authorization header to the backend (does NOT inject the server key) —
// so the /visits admin page is genuinely gated: you must supply the API key to see anything.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8080";

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.search || "?limit=1000";  // forward limit + app_only
  const res = await fetch(`${BACKEND_URL}/visits${qs}`, {
    headers: { Authorization: req.headers.get("authorization") || "" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({ error: "bad backend response" }));
  return NextResponse.json(data, { status: res.status });
}
