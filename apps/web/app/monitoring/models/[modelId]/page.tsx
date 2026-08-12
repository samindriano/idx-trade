"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { FINAL_RANKER, O2_CHALLENGER, V2_CHAMPION } from "@/lib/model-catalog";

type RuntimeModelRun = {
  session_date: string;
  model_id: string;
  state: string;
  artifact_sha256?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
};

type MonitorRuntimeStatus = {
  data_ready_sessions: number;
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

function shortDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default function ModelDetailPage() {
  const params = useParams<{ modelId: string }>();
  const model = params.modelId === "o2" ? O2_CHALLENGER : params.modelId === "v2" ? V2_CHAMPION : FINAL_RANKER;
  const [status, setStatus] = useState<MonitorRuntimeStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/monitor/status", { cache: "no-store" });
      const payload = (await response.json()) as StatusResponse;
      setConnected(Boolean(payload.connected));
      if (payload.status) {
        setStatus(payload.status);
        setError(null);
      } else {
        setError(payload.error ?? "Runtime unavailable");
      }
    } catch (reason) {
      setConnected(false);
      setError(reason instanceof Error ? reason.message : "Runtime unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const modelRuns = useMemo(
    () => (status?.model_runs ?? [])
      .filter((run) => run.model_id === model.id)
      .sort((a, b) => b.session_date.localeCompare(a.session_date)),
    [model.id, status],
  );
  const scoredRuns = modelRuns.filter((run) => run.state === "DONE" && Boolean(run.artifact_sha256));
  const failedRuns = modelRuns.filter((run) => run.state === "FAILED" || run.error_code);
  const latestScored = scoredRuns[0] ?? null;
  const latestRun = modelRuns[0] ?? null;
  const coverage = Math.min(100, scoredRuns.length);

  return (
    <main className="appShell monitorShell">
      <header className="topNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a href="/#overview">Overview</a>
            <a className="active" href="/monitoring">Forward Monitoring</a>
          </nav>
        </div>
      </header>

      <div className="page modelDetailPage">
        <a className="modelDetailBack" href="/monitoring">Back to Forward Monitoring</a>

        <section className="modelDetailHero">
          <div>
            <p className="overviewKicker">FORWARD PERFORMANCE</p>
            <h1>{model.shortName}</h1>
            <p>{params.modelId === "o2" ? "Primary challenger detail, paired against the V3-B incumbent. This view reports score-artifact progress only." : "Detailed forward-session evidence for this model. This view reports score-artifact progress only."}</p>
          </div>
        </section>

        <section className="modelDetailMetrics" aria-label="Forward model performance summary">
          <article><span>SCORE COVERAGE</span><strong>{loading ? "—" : scoredRuns.length}<em>{!loading && `/ ${model.forwardTargetSessions}`}</em></strong><small>verified score artifacts</small></article>
          <article className="latestScoredMetric"><span>LATEST SCORED</span><strong>{loading ? "Reading..." : shortDate(latestScored?.session_date)}</strong><small>most recent forward session</small></article>
          <article><span>LATEST RUN</span><strong>{loading ? "Reading..." : latestRun?.state ?? "Not started"}</strong><small>{loading ? "Waiting for status" : formatTimestamp(latestRun?.completed_at)}</small></article>
          <article><span>RUN ISSUES</span><strong>{loading ? "—" : failedRuns.length}</strong><small>failed or incomplete runs</small></article>
        </section>

        <section className="modelDetailGrid">
          <article className="modelDetailCard modelDetailProgressCard">
            <div className="modelDetailCardHead"><div><span>FORWARD ACCUMULATION</span><h2>Score artifact progress</h2></div><strong>{loading ? "—" : `${coverage}%`}</strong></div>
            <div className={`modelDetailProgress ${loading ? "isLoading" : ""}`}><span style={{ width: `${loading ? 0 : coverage}%` }} /></div>
            <dl className="modelDetailFacts">
              <div><dt>Model ID</dt><dd>{model.id}</dd></div>
              <div><dt>Feature contract</dt><dd>{model.featureCount} features</dd></div>
              <div><dt>Model SHA</dt><dd>{model.modelSha256.slice(0, 14)}...</dd></div>
            </dl>
          </article>

          <article className="modelDetailCard modelDetailNoteCard">
            <span>READING THE RESULT</span>
            <h2>What this page measures</h2>
            <p>This page confirms whether the model has produced a valid forward score artifact for each captured session.</p>
            <p>It reports forward score evidence only; realized returns and other outcome metrics are not shown here.</p>
          </article>
        </section>

        <section className="modelDetailRuns">
          <div className="modelDetailRunsHead"><div><span>FORWARD SESSION HISTORY</span><h2>Recent score runs</h2></div><small>{loading ? "Reading runtime..." : `${modelRuns.length} run(s) recorded`}</small></div>
          {loading ? (
            <div className="modelDetailLoading"><i />Reading forward score artifacts...</div>
          ) : modelRuns.length ? (
            <div className="modelDetailRunGrid">
              {modelRuns.map((run) => (
                <article className="modelDetailRun" key={`${run.model_id}-${run.session_date}`}>
                  <div><span>{shortDate(run.session_date)}</span><strong className={run.state === "DONE" ? "runStateDone" : "runStateOther"}>{run.state === "DONE" ? "Scored" : run.state}</strong></div>
                  <small>{run.artifact_sha256 ? `Artifact ${run.artifact_sha256.slice(0, 14)}...` : run.error_message ?? "No score artifact"}</small>
                  {run.completed_at && <time dateTime={run.completed_at}>{formatTimestamp(run.completed_at)}</time>}
                </article>
              ))}
            </div>
          ) : (
            <div className="modelDetailEmpty">No forward score artifact has been produced for this model yet.</div>
          )}
          {error && <div className="modelDetailError">{error}</div>}
        </section>
      </div>
    </main>
  );
}
