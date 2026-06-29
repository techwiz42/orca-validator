import { NextRequest, NextResponse } from "next/server";

import { backendFetch } from "@/lib/backend";

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const format = req.nextUrl.searchParams.get("format") === "docx" ? "docx" : "md";
  const res = await backendFetch(`/documents/${params.id}/revised.${format}`);
  if (!res.ok) {
    return NextResponse.json({ error: "no revised document" }, { status: res.status });
  }
  const body = await res.arrayBuffer();
  return new NextResponse(body, {
    status: 200,
    headers: {
      "content-type": res.headers.get("content-type") || "application/octet-stream",
      "content-disposition":
        res.headers.get("content-disposition") || `attachment; filename="revised.${format}"`,
    },
  });
}
