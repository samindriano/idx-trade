"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { FINAL_RANKER, O2_CHALLENGER, V2_CHAMPION } from "@/lib/model-catalog";

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
  state: string;
  artifact_sha256?: string | null;
  error_code?: string | null;
  error_message?: string | null;
};

type MonitorRuntimeStatus = {
  monitor_start_date: string;
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

type MonitoredModel = {
  id: string;
  route: "o2" | "v3" | "v2";
  shortName: string;
  generation: string;
  featureCount: number;
  modelSha256: string;
  forwardTargetSessions: number;
  role: string;
  note: string;
  accent: "challenger" | "incumbent" | "baseline";
};

const MONITORED_MODELS: readonly MonitoredModel[] = [
  {
    ...O2_CHALLENGER,
    route: "o2",
    role: "Primary challenger",
    note: "Historical leader; monitored on the same sessions as both references.",
    accent: "challenger",
  },
  {
    ...FINAL_RANKER,
    route: "v3",
    role: "Incumbent reference",
    note: "Current incumbent; retained as the prospective comparison anchor.",
    accent: "incumbent",
  },
  {
    ...V2_CHAMPION,
    route: "v2",
    role: "Historical baseline",
    note: "Original champion; kept in the monitoring lane for a fair three-model record.",
    accent: "baseline",
  },
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

function shortSessionDate(value: string) {
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function sessionLabel(state: SessionState) {
  if (state === "DATA_READY") return "Ready";
  if (state === "FETCHING") return "Fetching";
  if (state === "DATA_FAILED") return "Failed";
  return "Waiting";
}

function modelArtifactDates(status: MonitorRuntimeStatus | null, modelId: string) {
  if (!status) return new Set<string>();
  return new Set(
    status.model_runs
      .filter((run) => run.model_id === modelId && run.state === "DONE" && Boolean(run.artifact_sha256))
      .map((run) => run.session_date),
  );
}

function modelProgressLabel(count: number, target: number) {
  return `${count} / ${target}`;
}

export default function MonitoringPage() {
  const [status, setStatus] = useState<MonitorRuntimeStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [requestDetail, setRequestDetail] = useState<string | null>(null);

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

  const modelDates = useMemo(
    () => Object.fromEntries(MONITORED_MODELS.map((model) => [model.id, modelArtifactDates(status, model.id)])) as Record<string, Set<string>>,
    [status],
  );

  const sharedScoredDates = useMemo(() => {
    const [first, ...rest] = MONITORED_MODELS.map((model) => modelDates[model.id] ?? new Set<string>());
    if (!first) return new Set<string>();
    return new Set([...first].filter((date) => rest.every((dates) => dates.has(date))));
  }, [modelDates]);

  const latestReadySession = useMemo(
    () => [...(status?.sessions ?? [])].reverse().find((session) => session.state === "DATA_READY") ?? null,
    [status],
  );

  const latestFailure = useMemo(
    () => [...(status?.sessions ?? [])].reverse().find((session) => session.state === "DATA_FAILED") ?? null,
    [status],
  );

  const runtimeLabel = statusLoading
    ? "Reading automated archive"
    : configured && connected
      ? "Automated archive connected"
      : configured
        ? "Runtime unavailable"
        : "Runtime not configured";

  return (
    <main className="appShell monitorShell">
      <header className="topNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a href="/#overview">Overview</a>
            <a className="active" href="/monitoring">Forward Monitoring</a>
            <a href="/compare">Compare</a>
          </nav>
        </div>
      </header>

      <div className="page monitoringPage">
        <section className="monitorHero">
          <div>
            <p className="eyebrow">FORWARD MODEL OBSERVATORY</p>
            <h1>Forward Monitoring</h1>
            <p className="heroCopy">One automated session archive, three monitored ranking models, and one shared prospective record.</p>
          </div>
        </section>

        <section className="monitorSummaryGrid monitorSummaryGridThree" aria-label="Monitoring summary">
          <article className="summaryBlock prominent"><span>Monitored models</span><strong>3</strong><small>O2 · V3-B · V2</small></article>
          <article className="summaryBlock"><span>Latest EOD archive</span><strong>{statusLoading ? "—" : shortDate(latestReadySession?.session_date ?? null)}</strong><small>{status?.data_ready_sessions ?? 0} ready sessions</small></article>
          <article className="summaryBlock"><span>Shared score sessions</span><strong>{statusLoading ? "—" : sharedScoredDates.size}</strong><small>all three models</small></article>
        </section>

        <section className="surface autoArchivePanel" aria-labelledby="archive-title">
          <div className="autoArchiveHead">
            <div>
              <span className="panelKicker">AUTOMATED SESSION ARCHIVE</span>
              <h2 id="archive-title">EOD and intraday evidence</h2>
              <p>The runtime retrieves market evidence automatically. This page is read-only and reflects the immutable session and score artifacts it finds; there is no manual capture action here.</p>
            </div>
            <div className={`archiveConnection ${configured && connected ? "isConnected" : "isUnavailable"}`}>
              <i aria-hidden="true" />
              <strong>{runtimeLabel}</strong>
            </div>
          </div>

          <div className="archiveFacts">
            <div><span>Latest ready session</span><strong>{statusLoading ? "—" : shortDate(latestReadySession?.session_date ?? null)}</strong><small>official EOD archive</small></div>
            <div><span>Next expected session</span><strong>{statusLoading ? "—" : shortDate(status?.next_missing_session ?? null)}</strong><small>runtime queue</small></div>
            <div><span>Archive range</span><strong>{statusLoading ? "—" : `${shortDate(status?.monitor_start_date ?? null)} → ${shortDate(status?.calendar_last_session ?? null)}`}</strong><small>configured monitoring window</small></div>
          </div>

          {requestError && (
            <div className="runtimeNotice danger"><i /><div><strong>{requestError}</strong>{requestDetail && <p>{requestDetail}</p>}</div></div>
          )}
          {latestFailure && !requestError && (
            <div className="runtimeNotice danger"><i /><div><strong>{shortDate(latestFailure.session_date)} · Session failed</strong><p>{latestFailure.error_message ?? latestFailure.error_code ?? "See runtime diagnostics."}</p></div></div>
          )}

          <div className="sessionArchiveHead">
            <div><span className="panelKicker">RECENT SESSIONS</span><h3>Archive activity</h3></div>
            <small>{statusLoading ? "Reading runtime..." : "Updates automatically"}</small>
          </div>
          {statusLoading ? (
            <div className="loadingSessionState"><i />Reading forward session status...</div>
          ) : status?.sessions.length ? (
            <div className="sessionStrip">
              {status.sessions.slice(-12).map((session) => (
                <div key={session.session_date} className={`sessionTile ${session.state.toLowerCase()}`} title={session.error_message ?? undefined}>
                  <span>{shortSessionDate(session.session_date)}</span>
                  <strong>{sessionLabel(session.state)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="emptySessionState"><strong>No sessions in the archive yet</strong></div>
          )}
        </section>

        <section className="monitoringModelsSection" aria-labelledby="models-title">
          <div className="monitoringSectionHead">
            <div><span className="panelKicker">MONITORED MODELS</span><h2 id="models-title">Prospective score coverage</h2></div>
            <p>Each model is scored independently on the same automated session archive. Select a model for its detailed history.</p>
          </div>
          <div className="monitoredModelGrid">
            {MONITORED_MODELS.map((model) => {
              const count = statusLoading ? 0 : modelDates[model.id]?.size ?? 0;
              const progress = statusLoading ? 0 : Math.min(100, (count / model.forwardTargetSessions) * 100);
              return (
                <a key={model.id} className={`surface monitoredModelCard ${model.accent}`} href={`/monitoring/models/${model.route}`} aria-label={`View forward detail for ${model.shortName}`}>
                  <div className="monitoredModelTopline"><span>{model.role}</span><b>{model.generation}</b></div>
                  <h3>{model.shortName}</h3>
                  <div className="monitoredModelScore"><strong>{statusLoading ? "—" : count}</strong><span>/ {model.forwardTargetSessions} sessions</span></div>
                  <div className={`progressTrack ${statusLoading ? "isLoading" : ""}`}><span style={{ width: `${progress}%` }} /></div>
                  <p>{model.note}</p>
                  <div className="monitoredModelMeta"><span>{modelArtifactDates(status, model.id).size ? "Score artifacts available" : "Awaiting score artifacts"}</span><span>{model.featureCount} features</span></div>
                  <div className="modelCardAction"><span>View model detail</span><b aria-hidden="true">→</b></div>
                </a>
              );
            })}
          </div>
        </section>

        <section className="surface alignmentPanel" aria-labelledby="alignment-title">
          <div className="monitoringSectionHead compactHead">
            <div><span className="panelKicker">SESSION ALIGNMENT</span><h2 id="alignment-title">One record across all three models</h2></div>
            <span className="alignmentBadge">SAME ARCHIVE</span>
          </div>
          <p>Shared score sessions count only when O2, V3-B, and V2 each have a verified artifact for the same official session. Missing artifacts remain visible as gaps; they are never inferred.</p>
          <div className="alignmentMetrics">
            {MONITORED_MODELS.map((model) => (
              <div key={model.id}><span>{model.generation}</span><strong>{statusLoading ? "—" : modelProgressLabel(modelDates[model.id]?.size ?? 0, model.forwardTargetSessions)}</strong><small>{model.role}</small></div>
            ))}
            <div><span>Shared</span><strong>{statusLoading ? "—" : sharedScoredDates.size}</strong><small>same-session artifacts</small></div>
          </div>
          <small className="alignmentNote">Outcome metrics remain outside this read-only monitoring view until the authorized forward-validation gate opens.</small>
        </section>
      </div>
    </main>
  );
}
