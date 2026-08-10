import { NextRequest, NextResponse } from "next/server";

import {
  launchSessionCapture,
  MonitorRuntimeError,
  monitorRuntimeConfigured,
} from "@/lib/monitor-runtime";

export const dynamic = "force-dynamic";

function localOriginAllowed(request: NextRequest) {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  try {
    const url = new URL(origin);
    return url.hostname === "127.0.0.1" || url.hostname === "localhost" || url.hostname === "::1";
  } catch {
    return false;
  }
}

export async function POST(request: NextRequest) {
  if (!localOriginAllowed(request)) {
    return NextResponse.json({ error: "Monitoring mutation is local-only." }, { status: 403 });
  }
  if (!monitorRuntimeConfigured()) {
    return NextResponse.json(
      { error: "IDX_TRADE_RUNTIME_ROOT is not configured in apps/web/.env.local." },
      { status: 503 },
    );
  }

  let date: string | null = null;
  try {
    const body = (await request.json()) as { date?: unknown };
    if (typeof body.date === "string" && body.date.trim()) date = body.date.trim();
  } catch {
    // Empty JSON body means: automatically use the earliest missing official session.
  }

  if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return NextResponse.json({ error: "date must use YYYY-MM-DD." }, { status: 400 });
  }

  try {
    const result = await launchSessionCapture(date);
    return NextResponse.json(result, { status: result.accepted ? 202 : 200 });
  } catch (error) {
    const runtime = error as MonitorRuntimeError;
    return NextResponse.json(
      {
        error: runtime.message || "Session capture could not be started.",
        detail: runtime.detail ?? null,
      },
      { status: 409 },
    );
  }
}
