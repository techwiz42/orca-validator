import { NextRequest, NextResponse } from "next/server";

import { backendFetch } from "@/lib/backend";

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const res = await backendFetch(`/machines/${params.id}`);
  const data = await res.json().catch(() => ({ error: "bad backend response" }));
  return NextResponse.json(data, { status: res.status });
}
