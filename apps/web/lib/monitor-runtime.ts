import { execFile, spawn } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
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
  monitor_start_date: string;
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

export type StockbitIntradayStatus = {
  task_name: string;
  task_state: string;
  last_run_time: string | null;
  next_run_time: string | null;
  last_task_result: number | null;
  runtime_root: string | null;
  runtime_status: string;
  latest_session_date: string | null;
  latest_run_status: string | null;
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

function stockbitRuntimeRoot() {
  const explicit = process.env.IDX_TRADE_STOCKBIT_RUNTIME_ROOT?.trim();
  if (explicit) return explicit;
  const configured = process.env.IDX_TRADE_RUNTIME_ROOT?.trim();
  return configured ? path.join(configured, "stockbit_intraday_recurring_v1") : null;
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
    "idx_trade.forward_monitoring_runtime",
    command,
    "--runtime-root",
    runtimeRoot(),
  ];
}

export async function getMonitorRuntimeStatus(): Promise<MonitorRuntimeStatus> {
  return runJson<MonitorRuntimeStatus>(baseArgs("status"));
}

function powershellLiteral(value: string) {
  return `'${value.replace(/'/g, "''")}'`;
}

async function getStockbitTaskStatus(taskName: string) {
  if (process.platform !== "win32") return { task_state: "UNSUPPORTED", last_run_time: null, next_run_time: null, last_task_result: null };
  const script = [
    `$task = Get-ScheduledTask -TaskName ${powershellLiteral(taskName)} -ErrorAction SilentlyContinue`,
    `if (-not $task) { [pscustomobject]@{ task_state = 'MISSING'; last_run_time = $null; next_run_time = $null; last_task_result = $null } | ConvertTo-Json -Compress; exit 0 }`,
    `$info = Get-ScheduledTaskInfo -TaskName ${powershellLiteral(taskName)}`,
    `[pscustomobject]@{ task_state = [string]$task.State; last_run_time = if ($info.LastRunTime) { $info.LastRunTime.ToString('o') } else { $null }; next_run_time = if ($info.NextRunTime) { $info.NextRunTime.ToString('o') } else { $null }; last_task_result = [int]$info.LastTaskResult } | ConvertTo-Json -Compress`,
  ].join("; ");
  try {
    const { stdout } = await execFileAsync("powershell.exe", ["-NoProfile", "-Command", script], {
      timeout: 5_000,
      windowsHide: true,
      maxBuffer: 128 * 1024,
    });
    return JSON.parse(stdout.trim()) as { task_state: string; last_run_time: string | null; next_run_time: string | null; last_task_result: number | null };
  } catch {
    return { task_state: "UNAVAILABLE", last_run_time: null, next_run_time: null, last_task_result: null };
  }
}

export async function getStockbitIntradayStatus(): Promise<StockbitIntradayStatus> {
  const taskName = process.env.IDX_TRADE_STOCKBIT_TASK_NAME?.trim() || "IDX-Trade Stockbit Intraday Daily";
  const task = await getStockbitTaskStatus(taskName);
  const root = stockbitRuntimeRoot();
  let latestSessionDate: string | null = null;
  let latestRunStatus: string | null = null;
  let runtimeStatus = root ? "NO_CAPTURE_ARTIFACT" : "NOT_CONFIGURED";
  if (root) {
    try {
      const sessionsRoot = path.join(root, "sessions");
      const sessionDirs = (await readdir(sessionsRoot, { withFileTypes: true }))
        .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
        .map((entry) => entry.name)
        .sort();
      latestSessionDate = sessionDirs.at(-1) ?? null;
      if (latestSessionDate) {
        const summaryPath = path.join(sessionsRoot, latestSessionDate, "final", "run_summary.json");
        const summary = JSON.parse(await readFile(summaryPath, "utf8")) as { complete?: boolean; status?: string };
        latestRunStatus = summary.complete === true ? "COMPLETE" : String(summary.status ?? "INCOMPLETE");
        runtimeStatus = latestRunStatus === "COMPLETE" ? "CAPTURED" : "INCOMPLETE_ARTIFACT";
      }
    } catch {
      runtimeStatus = "NO_CAPTURE_ARTIFACT";
    }
  }
  return {
    task_name: taskName,
    task_state: task.task_state,
    last_run_time: task.last_run_time,
    next_run_time: task.next_run_time,
    last_task_result: task.last_task_result,
    runtime_root: root,
    runtime_status: runtimeStatus,
    latest_session_date: latestSessionDate,
    latest_run_status: latestRunStatus,
  };
}

export async function syncMonitorCalendar() {
  return runJson<{
    status: string;
    monitor_start_date: string;
    sessions: number;
    first: string | null;
    last: string | null;
  }>(baseArgs("sync-calendar"), 60_000);
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

  if (target < status.monitor_start_date) {
    throw new MonitorRuntimeError(
      `Target ${target} is before monitor start ${status.monitor_start_date}.`,
    );
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
