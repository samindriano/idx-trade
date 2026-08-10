"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type SessionState = "AVAILABLE" | "FETCHING" | "DATA_READY" | "DATA_FAILED";

type MonitorSession = {
  session_date: string;
  state: SessionState;
  error_code: string | null;
  error_message: string | null;
  completed_at: string | null;
};

type RuntimeModelRun = {
  session_date: string;
  model_id: string;
  model_fingerprint: string;
  generation: string;
  state: string;
  progress_fraction: number;
  artifact_sha256?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
};

type MonitorRuntimeStatus = {
  runtime_ready: boolean;
  monitor_start_date: string;
  calendar_ready: boolean;
  calendar_first_session: string | null;
  calendar_last_session: string | null;
  next_missing_session: string | null;
  data_ready_sessions: number;
  sessions: MonitorSession[];
  model_runs: RuntimeModelRun[];
  outcome_access: "LOCKED";
};

type StatusResponse = {
  connected: boolean;
  configured: boolean;
  status?: MonitorRuntimeStatus;
  error?: string;
  detail?: string | null;
};

type GenerationSlot = {
  generation: "V2" | "V3" | "V4";
  modelId: string;
  name: string;
  frozen: boolean;
  targetSessions: number | null;
};

const generationSlots: GenerationSlot[] = [
  { generation: "V2", modelId: "HGB_XS_MARKET", name: "HGB XS + Market", frozen: true, targetSessions: 100 },
  { generation: "V3", modelId: "FUTURE_V3_CHAMPION", name: "Future champion", frozen: false, targetSessions: null },
  { generation: "V4", modelId: "FUTURE_V4_CHAMPION", name: "Future champion", frozen: false, targetSessions: null },
];

function Logo() {
  return <div className="brandMark" aria-hidden="true"><span /><span /><span /><span /></div>;
}

function shortDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function buttonDate(value: string | null) {
  if (!value) return "Next Session";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function sessionLabel(state: SessionState) {
  if (state === "DATA_READY") return "Recorded";
  if (state === "FETCHING") return "Fetching";
  if (state === "DATA_FAILED") return "Failed";
  return "Missing";
}

export default function MonitoringPage() {
  const [status, setStatus] = useState<MonitorRuntimeStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [requestDetail, setRequestDetail] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [targetDate, setTargetDate] = useState("");

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/monitor/status", { cache: "no-store" });
      const payload = (await response.json()) as StatusResponse;
      setConnected(Boolean(payload.connected));
      setConfigured(Boolean(payload.configured));
      if (payload.status) {
        setStatus(payload.status);
        setRequestError(null);
        setRequestDetail(null);
        setTargetDate((current) => {
          const floor = payload.status?.monitor_start_date ?? "";
          if (!current || (floor && current < floor)) return payload.status?.next_missing_session || floor;
          return current;
        });
      } else {
        setRequestError(payload.error ?? "Runtime unavailable");
        setRequestDetail(payload.detail ?? null);
      }
    } catch (error) {
      setConnected(false);
      setRequestError(error instanceof Error ? error.message : "Runtime unavailable");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!status) return;
    if (targetDate && targetDate < status.monitor_start_date) {
      setTargetDate(status.next_missing_session || status.monitor_start_date);
      return;
    }
    if (!status.next_missing_session) return;
    const selected = status.sessions.find((item) => item.session_date === targetDate);
    if (!targetDate || selected?.state === "DATA_READY") setTargetDate(status.next_missing_session);
  }, [status, targetDate]);

  async function capture() {
    setSubmitting(true);
    setRequestError(null);
    setRequestDetail(null);
    try {
      const response = await fetch("/api/monitor/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: targetDate || null }),
      });
      const payload = (await response.json()) as {
        accepted?: boolean;
        target_session?: string | null;
        reason?: string;
        error?: string;
        detail?: string | null;
      };
      if (!response.ok) {
        throw new Error(payload.detail ? `${payload.error ?? "Capture failed"} — ${payload.detail}` : payload.error ?? "Capture failed");
      }
      if (payload.reason === "NO_MISSING_SESSION") setRequestError("All closed sessions are recorded.");
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      await refresh();
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Capture failed");
    } finally {
      setSubmitting(false);
    }
  }

  const v2DoneDates = useMemo(() => {
    if (!status) return new Set<string>();
    return new Set(
      status.model_runs
        .filter((run) => run.model_id === "HGB_XS_MARKET" && run.state === "DONE" && Boolean(run.artifact_sha256))
        .map((run) => run.session_date),
    );
  }, [status]);

  const latestRuns = useMemo(() => {
    const map = new Map<string, RuntimeModelRun>();
    for (const run of status?.model_runs ?? []) {
      const existing = map.get(run.model_id);
      if (!existing || run.session_date >= existing.session_date) map.set(run.model_id, run);
    }
    return map;
  }, [status]);

  const latestFailure = [...(status?.sessions ?? [])].reverse().find((session) => session.state === "DATA_FAILED");
  const anyFetching = status?.sessions.some((session) => session.state === "FETCHING") ?? false;
  const calendarReady = status?.calendar_ready ?? false;
  const captureTarget = targetDate || status?.next_missing_session || null;
  const canCapture = configured && connected && !submitting && !anyFetching;

  return (
    <main className="appShell monitorShell">
      <header className="topNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a href="/#overview">Overview</a>
            <a className="active" href="/monitoring">Forward Monitoring</a>
          </nav>
          <div className="researchPill"><span className="liveDot" /> Research only</div>
        </div>
      </header>

      <div className="page monitoringPage">
        <section className="monitorHero">
          <div><p className="eyebrow">V2 CHAMPION</p><h1>Forward Monitoring</h1></div>
          <div className="monitorHeroBadges">
            <span className="lockBadge"><span className="lockDot" /> Outcomes locked</span>
            <span className={`runtimeBadge ${connected ? "online" : "offline"}`}><i /> {connected ? "Runtime connected" : "Runtime offline"}</span>
          </div>
        </section>

        <section className="monitorSummaryGrid">
          <article className="summaryBlock prominent"><span>V2 progress</span><div><strong>{v2DoneDates.size}</strong><em>/ 100</em></div></article>
          <article className="summaryBlock"><span>Snapshots</span><strong>{status?.data_ready_sessions ?? 0}</strong></article>
          <article className="summaryBlock"><span>Next session</span><strong className="summaryTextValue">{shortDate(status?.next_missing_session ?? null)}</strong></article>
          <article className="summaryBlock"><span>Outcomes</span><strong className="summaryTextValue">LOCKED</strong></article>
        </section>

        <section className="monitorMainGrid">
          <article className="surface sessionCapturePanel">
            <div className="sectionHead"><div><span>SESSION DATA</span><h2>Capture</h2></div></div>
            <div className="captureBody">
              <div className="captureControls">
                <label>
                  <span>Target session</span>
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(event) => setTargetDate(event.target.value)}
                    min={status?.monitor_start_date ?? "2026-08-10"}
                    max={status?.calendar_last_session ?? undefined}
                  />
                </label>
                <button className="captureButton" type="button" disabled={!canCapture} onClick={() => void capture()}>
                  {submitting ? "Starting..." : anyFetching ? "Fetching..." : `Ambil Data ${buttonDate(captureTarget)}`}
                </button>
              </div>

              {!configured && <div className="runtimeNotice"><i /><div><strong>Runtime not configured</strong></div></div>}
              {configured && !calendarReady && connected && <div className="runtimeNotice info"><i /><div><strong>Calendar syncs on first capture</strong></div></div>}
              {requestError && <div className="runtimeNotice danger"><i /><div><strong>{requestError}</strong>{requestDetail && <p>{requestDetail}</p>}</div></div>}
              {latestFailure && !requestError && (
                <div className="runtimeNotice danger"><i /><div><strong>{shortDate(latestFailure.session_date)} · Failed</strong><p>{latestFailure.error_message ?? latestFailure.error_code ?? "Retry available"}</p></div></div>
              )}

              <div className="sessionStripHeader">
                <div><span>SESSION HISTORY</span><h3>Recent sessions</h3></div>
                <div className="sessionLegend">
                  <span><i className="legendDone" /> Recorded</span>
                  <span><i className="legendMissing" /> Missing</span>
                  <span><i className="legendFuture" /> Fetching</span>
                </div>
              </div>

              {status?.sessions.length ? (
                <div className="sessionStrip">
                  {status.sessions.slice(-12).map((session) => (
                    <button
                      type="button"
                      key={session.session_date}
                      className={`sessionTile ${session.state.toLowerCase()}`}
                      onClick={() => session.state !== "DATA_READY" && setTargetDate(session.session_date)}
                      title={session.error_message ?? undefined}
                    >
                      <span>{buttonDate(session.session_date)}</span>
                      <strong>{sessionLabel(session.state)}</strong>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="emptySessionState"><strong>No captured sessions</strong></div>
              )}
            </div>
          </article>

          <article className="surface v2ContractPanel">
            <div className="sectionHead compact">
              <div><span>ACTIVE MODEL</span><h2>HGB XS + Market</h2></div>
              <span className="modelBadge champion">V2</span>
            </div>
            <div className="contractProgress">
              <div className="contractNumber"><strong>{v2DoneDates.size}</strong><span>/ 100</span></div>
              <div className="progressTrack indigoTrack"><span style={{ width: `${v2DoneDates.size}%` }} /></div>
            </div>
            <div className="contractFacts">
              <div><span>Model</span><strong><i className="okDot" /> Frozen</strong></div>
              <div><span>SHA</span><strong>5c9e3d02…</strong></div>
              <div><span>Outcomes</span><strong>Locked</strong></div>
            </div>
          </article>
        </section>

        <section className="surface modelRunsPanel">
          <div className="sectionHead"><div><span>CHAMPION RUNS</span><h2>Model progress</h2></div></div>
          <div className="modelRunList">
            {generationSlots.map((slot) => {
              const run = latestRuns.get(slot.modelId);
              const progress = run?.progress_fraction ?? 0;
              const state = slot.frozen ? run?.state ?? "WAITING_FOR_DATA" : "NOT_FROZEN";
              return (
                <article className={`modelRunRow ${slot.frozen ? "" : "futureRun"}`} key={slot.modelId}>
                  <div className="runIdentity">
                    <span className={`generationPill ${slot.generation.toLowerCase()}`}>{slot.generation}</span>
                    <div><strong>{slot.name}</strong><small>{slot.frozen ? slot.modelId : "Not frozen"}</small></div>
                  </div>
                  <div className="runProgressBlock">
                    <div className="runProgressHead"><span>{state.replaceAll("_", " ")}</span>{slot.frozen && <em>{Math.round(progress * 100)}%</em>}</div>
                    <div className={`runTrack ${state === "FAILED" ? "failed" : ""}`}><span style={{ width: `${progress * 100}%` }} /></div>
                  </div>
                  <div className="runMeta">
                    {slot.frozen ? <><span>{v2DoneDates.size}/{slot.targetSessions ?? "—"} sessions</span><strong>{run?.artifact_sha256 ? "Verified" : "Waiting"}</strong></> : <strong>Inactive</strong>}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
