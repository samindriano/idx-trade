import { execFile, spawn } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export type SessionState = "AVAILABLE" | "FETCHING" | "DATA_READY" | "DATA_FAILED";

export type MonitorSession = {
  session_date: string;
  state: SessionState;
  error_code: string | null;
  error_message: string | null;
  completed_at: string | null;
};

export type RuntimeModelRun = {
  session_date: string;
  model_id: string;
  model_fingerprint: string;
  generation: string;
  state: string;
  progress_fraction: number;
  artifact_path?: string | null;
  artifact_sha256?: string | null;
  manifest_path?: string | null;
  manifest_sha256?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
};

export type MonitorRuntimeStatus = {
  schema_version: number;
  runtime_ready: boolean;
  runtime_root: string;
  calendar_ready: boolean;
  calendar_first_session: string | null;
  calendar_last_session: string | null;
  next_missing_session: string | null;
  data_ready_sessions: number;
  sessions: MonitorSession[];
  model_runs: RuntimeModelRun[];
  outcome_access: "LOCKED";
  forward_outcomes_accessed: false;
  generated_at_utc: string;
};

export class MonitorRuntimeError extends Error {
  constructor(message: string, public readonly detail?: string) {
    super(message);
    this.name = "MonitorRuntimeError";
  }
}

function repoRoot() {
  // Next.js is started from apps/web in the documented local workflow.
  return path.resolve(process.cwd(), "../..");
}

function runtimeRoot() {
  const value = process.env.IDX_TRADE_RUNTIME_ROOT?.trim();
  if (!value) {
    throw new MonitorRuntimeError(
      "Local monitoring runtime is not configured.",
      "Set IDX_TRADE_RUNTIME_ROOT once in apps/web/.env.local.",
    );
  }
  return value;
}

function pythonExecutable() {
  return process.env.IDX_TRADE_PYTHON?.trim() || "python";
}

function pythonEnv() {
  const root = repoRoot();
  const src = path.join(root, "src");
  const separator = process.platform === "win32" ? ";" : ":";
  const previous = process.env.PYTHONPATH?.trim();
  return {
    ...process.env,
    PYTHONPATH: previous ? `${src}${separator}${previous}` : src,
    PYTHONUNBUFFERED: "1",
  };
}

async function runJson<T>(args: string[], timeout = 20_000): Promise<T> {
  try {
    const { stdout, stderr } = await execFileAsync(pythonExecutable(), args, {
      cwd: repoRoot(),
      env: pythonEnv(),
      timeout,
      windowsHide: true,
      maxBuffer: 4 * 1024 * 1024,
    });
    const output = stdout.trim();
    if (!output) throw new MonitorRuntimeError("Python monitoring command returned no output.", stderr.trim());
    return JSON.parse(output) as T;
  } catch (error) {
    if (error instanceof MonitorRuntimeError) throw error;
    const value = error as { message?: string; stderr?: string; stdout?: string };
    throw new MonitorRuntimeError(
      value.message || "Local monitoring command failed.",
      value.stderr?.trim() || value.stdout?.trim(),
    );
  }
}

function baseArgs(command: "status" | "capture" | "sync-calendar") {
  return [
    "-m",
    "idx_trade.forward_monitoring",
    command,
    "--runtime-root",
    runtimeRoot(),
  ];
}

export async function getMonitorRuntimeStatus(): Promise<MonitorRuntimeStatus> {
  return runJson<MonitorRuntimeStatus>(baseArgs("status"));
}

export async function syncMonitorCalendar() {
  return runJson<{ status: string; sessions: number; first: string | null; last: string | null }>(
    baseArgs("sync-calendar"),
    60_000,
  );
}

export async function launchSessionCapture(requestedDate?: string | null) {
  // Calendar synchronization is deliberately synchronous and lightweight enough
  // for a local operator action. It makes invalid/holiday/skip requests fail before
  // a detached capture worker is launched.
  await syncMonitorCalendar();
  const status = await getMonitorRuntimeStatus();
  const target = requestedDate?.trim() || status.next_missing_session;
  if (!target) {
    return { accepted: false as const, reason: "NO_MISSING_SESSION", target_session: null };
  }

  const session = status.sessions.find((item) => item.session_date === target);
  if (!session) {
    throw new MonitorRuntimeError(`Target ${target} is not a closed official IDX session.`);
  }
  if (session.state === "DATA_READY") {
    return { accepted: false as const, reason: "ALREADY_READY", target_session: target };
  }
  if (status.next_missing_session && target !== status.next_missing_session) {
    throw new MonitorRuntimeError(
      `Earlier missing session must be captured first: ${status.next_missing_session}.`,
    );
  }

  const child = spawn(
    pythonExecutable(),
    [...baseArgs("capture"), "--date", target],
    {
      cwd: repoRoot(),
      env: pythonEnv(),
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    },
  );
  child.unref();
  return { accepted: true as const, target_session: target, pid: child.pid ?? null };
}

export function monitorRuntimeConfigured() {
  return Boolean(process.env.IDX_TRADE_RUNTIME_ROOT?.trim());
}
