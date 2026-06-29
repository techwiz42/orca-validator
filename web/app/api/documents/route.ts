import { NextRequest, NextResponse } from "next/server";

import { backendFetch } from "@/lib/backend";

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const res = await backendFetch("/documents", { method: "POST", body: form });
  const data = await res.json().catch(() => ({ error: "bad backend response" }));
  return NextResponse.json(data, { status: res.status });
}
