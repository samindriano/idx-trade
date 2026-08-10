import { NextResponse } from "next/server";

import {
  getMonitorRuntimeStatus,
  MonitorRuntimeError,
  monitorRuntimeConfigured,
} from "@/lib/monitor-runtime";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!monitorRuntimeConfigured()) {
    return NextResponse.json({
      connected: false,
      configured: false,
      error: "IDX_TRADE_RUNTIME_ROOT is not configured in apps/web/.env.local.",
    });
  }

  try {
    const status = await getMonitorRuntimeStatus();
    return NextResponse.json({ connected: true, configured: true, status });
  } catch (error) {
    const runtime = error as MonitorRuntimeError;
    return NextResponse.json(
      {
        connected: false,
        configured: true,
        error: runtime.message || "Local monitoring runtime is unavailable.",
        detail: runtime.detail ?? null,
      },
      { status: 503 },
    );
  }
}
