"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { FINAL_RANKER, V2_CHAMPION } from "@/lib/model-catalog";

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

const monitoringLayers = [
  {
    title: "Data capture",
    state: "ACTIVE",
    copy: "Official-session snapshot, PIT universe evidence, canonical EOD prices, artifact hashes, and capture failures.",
  },
  {
    title: "Signal scoring",
    state: "V3-B + V2 CHAMPION",
    copy: "Persist independent same-day cross-sectional score/rank artifacts for the frozen V3-B ranker and V2 champion.",
  },
  {
    title: "Forward accumulation",
    state: "100 SESSIONS",
    copy: "Count only verified final-ranker score artifacts. H10 maturity metadata can be tracked without opening realized outcomes.",
  },
  {
    title: "Outcome vault",
    state: "LOCKED",
    copy: "PR-AUC, ROC-AUC, Q5−Q1, TP/SL results, realized returns, and PnL stay hidden until the frozen one-shot block opens.",
  },
];

export default function MonitoringPage() {
  const [status, setStatus] = useState<MonitorRuntimeStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
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
    } finally {
      setStatusLoading(false);
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

  const finalScoredDates = useMemo(() => {
    if (!status) return new Set<string>();
    return new Set(
      status.model_runs
        .filter((run) => run.model_id === FINAL_RANKER.id && run.state === "DONE" && Boolean(run.artifact_sha256))
        .map((run) => run.session_date),
    );
  }, [status]);

  const v2ScoredDates = useMemo(() => {
    if (!status) return new Set<string>();
    return new Set(
      status.model_runs
        .filter((run) => run.model_id === V2_CHAMPION.id && run.state === "DONE" && Boolean(run.artifact_sha256))
        .map((run) => run.session_date),
    );
  }, [status]);

  const latestFailure = [...(status?.sessions ?? [])].reverse().find((session) => session.state === "DATA_FAILED");
  const anyFetching = status?.sessions.some((session) => session.state === "FETCHING") ?? false;
  const calendarReady = status?.calendar_ready ?? false;
  const captureTarget = targetDate || status?.next_missing_session || null;
  const canCapture = !statusLoading && configured && connected && !submitting && !anyFetching;
  const scoringProgress = Math.min(100, finalScoredDates.size);

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
          <div>
            <p className="eyebrow">FINAL V3-B · OUTCOME-BLIND</p>
            <h1>Forward Monitoring</h1>
            <p className="heroCopy">Capture EOD data and track the frozen V2 and V3-B rankers. Outcomes stay locked.</p>
          </div>
          <div className="monitorHeroBadges">
            <span className="lockBadge"><span className="lockDot" /> Outcomes locked</span>
            <span className={`runtimeBadge ${statusLoading ? "checking" : connected ? "online" : "offline"}`}><i /> {statusLoading ? "Checking runtime" : connected ? "Runtime connected" : "Runtime offline"}</span>
          </div>
        </section>

        <section className="monitorSummaryGrid">
          <article className="summaryBlock prominent"><span>Final V3-B scores</span><div><strong>{statusLoading ? "—" : finalScoredDates.size}</strong>{!statusLoading && <em>/ {FINAL_RANKER.forwardTargetSessions}</em>}</div></article>
          <article className="summaryBlock"><span>EOD snapshots</span><strong>{statusLoading ? "—" : status?.data_ready_sessions ?? 0}</strong></article>
          <article className="summaryBlock"><span>Next session</span><strong className="summaryTextValue">{statusLoading ? "—" : shortDate(status?.next_missing_session ?? null)}</strong></article>
          <article className="summaryBlock"><span>Outcome vault</span><strong className="summaryTextValue">LOCKED</strong></article>
        </section>

        <section className="monitorMainGrid">
          <article className="surface sessionCapturePanel">
            <div className="sectionHead"><div><span>SESSION DATA</span><h2>Capture EOD data</h2></div></div>
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
                  {statusLoading ? "Reading runtime..." : submitting ? "Starting..." : anyFetching ? "Fetching..." : `Capture EOD ${buttonDate(captureTarget)}`}
                </button>
              </div>

              {!statusLoading && !configured && <div className="runtimeNotice"><i /><div><strong>Runtime not configured</strong></div></div>}
              {configured && !calendarReady && connected && <div className="runtimeNotice info"><i /><div><strong>Calendar syncs on first capture</strong></div></div>}
              {requestError && <div className="runtimeNotice danger"><i /><div><strong>{requestError}</strong>{requestDetail && <p>{requestDetail}</p>}</div></div>}
              {latestFailure && !requestError && (
                <div className="runtimeNotice danger"><i /><div><strong>{shortDate(latestFailure.session_date)} · Failed</strong><p>{latestFailure.error_message ?? latestFailure.error_code ?? "Retry available"}</p></div></div>
              )}

              <div className="sessionStripHeader">
                <div><span>HISTORY</span><h3>Recent sessions</h3></div>
                <div className="sessionLegend">
                  <span><i className="legendDone" /> Recorded</span>
                  <span><i className="legendMissing" /> Missing</span>
                  <span><i className="legendFuture" /> Fetching</span>
                </div>
              </div>

              {statusLoading ? (
                <div className="loadingSessionState"><i />Reading forward session status...</div>
              ) : status?.sessions.length ? (
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

          <div className="modelCardsGrid" aria-label="Monitored models">
          <a className="surface modelCardLink finalModelPanel" href="/monitoring/models/v3" aria-label={`View forward detail for ${FINAL_RANKER.shortName}`}>
            <div className="sectionHead compact">
              <div><span>ACTIVE MODEL</span><h2>{FINAL_RANKER.shortName}</h2></div>
              <span className="modelBadge champion">FINAL V3</span>
            </div>
            <div className="contractProgress">
                <div className="contractNumber"><strong>{statusLoading ? "—" : finalScoredDates.size}</strong>{!statusLoading && <span>/ {FINAL_RANKER.forwardTargetSessions}</span>}</div>
                <div className={`progressTrack indigoTrack ${statusLoading ? "isLoading" : ""}`}><span style={{ width: `${statusLoading ? 0 : scoringProgress}%` }} /></div>
            </div>
            <div className="modelMeta">
              <span>{FINAL_RANKER.featureCount} features</span>
              <span>SHA {FINAL_RANKER.modelSha256.slice(0, 10)}...</span>
            </div>
            <div className="modelCardAction"><span>View forward detail</span><b aria-hidden="true">→</b></div>
          </a>

          <a className="surface modelCardLink finalModelPanel legacyChampionPanel" href="/monitoring/models/v2" aria-label={`View forward detail for ${V2_CHAMPION.shortName}`}>
            <div className="sectionHead compact">
              <div><span>V2 CHAMPION</span><h2>{V2_CHAMPION.shortName}</h2></div>
              <span className="modelBadge">FROZEN</span>
            </div>
            <div className="contractProgress">
                <div className="contractNumber"><strong>{statusLoading ? "—" : v2ScoredDates.size}</strong>{!statusLoading && <span>/ {V2_CHAMPION.forwardTargetSessions}</span>}</div>
                <div className={`progressTrack indigoTrack ${statusLoading ? "isLoading" : ""}`}><span style={{ width: `${statusLoading ? 0 : Math.min(100, v2ScoredDates.size)}%` }} /></div>
            </div>
            <div className="modelMeta">
              <span>{V2_CHAMPION.featureCount} features</span>
              <span>SHA {V2_CHAMPION.modelSha256.slice(0, 10)}...</span>
            </div>
            <div className="modelCardAction"><span>View forward detail</span><b aria-hidden="true">→</b></div>
          </a>
          </div>
        </section>

        <section className="surface modelRunsPanel">
          <div className="sectionHead"><div><span>RESEARCH LANES</span><h2>What is in the forward system</h2></div></div>
          <div className="modelRunList">
            <article className="modelRunRow">
              <div className="runIdentity"><span className="generationPill v3">V3</span><div><strong>Alpha ranker · {FINAL_RANKER.shortName}</strong><small>{FINAL_RANKER.id}</small></div></div>
              <div className="runMeta"><strong>ACTIVE / FROZEN</strong></div>
            </article>
            <article className="modelRunRow futureRun">
              <div className="runIdentity"><span className="generationPill v4">RISK</span><div><strong>Path Risk V1</strong><small>Separate historical research lane; not a forward trade filter yet.</small></div></div>
              <div className="runMeta"><strong>NOT INTEGRATED</strong></div>
            </article>
            <article className="modelRunRow futureRun">
              <div className="runIdentity"><span className="generationPill v4">P</span><div><strong>Probability / calibration</strong><small>No validated probability layer exists yet.</small></div></div>
              <div className="runMeta"><strong>NOT STARTED</strong></div>
            </article>
          </div>
        </section>
      </div>
    </main>
  );
}
