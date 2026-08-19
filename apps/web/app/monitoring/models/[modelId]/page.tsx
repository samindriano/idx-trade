"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { V2_CHAMPION } from "@/lib/model-catalog";
import { V4X_ALPHA } from "@/lib/v4x-catalog";

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
};

type DetailModel = {
  id: string;
  shortName: string;
  generation: string;
  featureCount: number;
  forwardTargetSessions: number;
  fingerprint: string;
  role: string;
  description: string;
};

const V4X_DETAIL: DetailModel = {
  id: V4X_ALPHA.id,
  shortName: V4X_ALPHA.shortName,
  generation: V4X_ALPHA.generation,
  featureCount: V4X_ALPHA.featureCount,
  forwardTargetSessions: V4X_ALPHA.forwardTargetSessions,
  fingerprint: V4X_ALPHA.modelBundleManifestSha256,
  role: "Current alpha candidate",
  description: "Frozen Geometry3 final refit. Historical evidence comes from V4-3R; exact X1 prospective performance is intentionally unknown until the forward vault opens.",
};

const V2_DETAIL: DetailModel = {
  id: V2_CHAMPION.id,
  shortName: `V2 ${V2_CHAMPION.shortName}`,
  generation: V2_CHAMPION.generation,
  featureCount: V2_CHAMPION.featureCount,
  forwardTargetSessions: V2_CHAMPION.forwardTargetSessions,
  fingerprint: V2_CHAMPION.modelSha256,
  role: "Reference model",
  description: "V2 HGB XS + Market is the original historical champion retained as the stable forward reference while V4-X is confirmed prospectively.",
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
  const isV2 = params.modelId === "v2";
  const model = isV2 ? V2_DETAIL : V4X_DETAIL;
  const [status, setStatus] = useState<MonitorRuntimeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/monitor/status", { cache: "no-store" });
      const payload = (await response.json()) as StatusResponse;
      if (payload.status) {
        setStatus(payload.status);
        setError(null);
      } else setError(payload.error ?? "Runtime unavailable");
    } catch (reason) {
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
    () => (status?.model_runs ?? []).filter((run) => run.model_id === model.id).sort((a, b) => b.session_date.localeCompare(a.session_date)),
    [model.id, status],
  );
  const scoredRuns = modelRuns.filter((run) => run.state === "DONE" && Boolean(run.artifact_sha256));
  const failedRuns = modelRuns.filter((run) => run.state === "FAILED" || run.error_code);
  const latestScored = scoredRuns[0] ?? null;
  const coverage = Math.min(100, (scoredRuns.length / model.forwardTargetSessions) * 100);

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
        <a className="modelDetailBack" href="/monitoring">← Back to Forward Monitoring</a>
        <section className="modelDetailHero">
          <div>
            <p className="overviewKicker">{model.role.toUpperCase()}</p>
            <h1>{model.shortName}</h1>
            <p>{model.description}</p>
          </div>
        </section>

        <section className="modelDetailMetrics" aria-label="Forward model summary">
          <article><span>SCORE COVERAGE</span><strong>{loading ? "—" : scoredRuns.length}<em>{!loading && `/ ${model.forwardTargetSessions}`}</em></strong><small>verified forward artifacts</small></article>
          <article className="latestScoredMetric"><span>LATEST SCORED</span><strong>{loading ? "Reading..." : shortDate(latestScored?.session_date)}</strong><small>most recent forward session</small></article>
          <article><span>{isV2 ? "HISTORICAL MEDIAN ΔPR" : "AUDITED HISTORICAL RANKIC"}</span><strong>{isV2 ? "+2.39%" : V4X_ALPHA.auditedCommonSupportConsensusIc.toFixed(3)}</strong><small>{isV2 ? "six V2 development folds" : `${V4X_ALPHA.historicalValidationSessions} walk-forward sessions`}</small></article>
          <article><span>RUN ISSUES</span><strong>{loading ? "—" : failedRuns.length}</strong><small>failed or incomplete runs</small></article>
        </section>

        <section className="modelDetailGrid">
          <article className="modelDetailCard modelDetailProgressCard">
            <div className="modelDetailCardHead"><div><span>FORWARD ACCUMULATION</span><h2>Score artifact progress</h2></div><strong>{loading ? "—" : `${coverage.toFixed(0)}%`}</strong></div>
            <div className={`modelDetailProgress ${loading ? "isLoading" : ""}`}><span style={{ width: `${loading ? 0 : coverage}%` }} /></div>
            <dl className="modelDetailFacts">
              <div><dt>Model ID</dt><dd>{model.id}</dd></div>
              <div><dt>Feature contract</dt><dd>{model.featureCount} features</dd></div>
              <div><dt>{isV2 ? "Model SHA" : "Bundle manifest"}</dt><dd>{model.fingerprint.slice(0, 14)}...</dd></div>
              {!isV2 && <div><dt>Common-support RankIC</dt><dd>{V4X_ALPHA.auditedCommonSupportConsensusIc.toFixed(3)}</dd></div>}
              {!isV2 && <div><dt>Strict-support RankIC</dt><dd>{V4X_ALPHA.auditedStrictSupportConsensusIc.toFixed(3)}</dd></div>}
            </dl>
          </article>

          <article className="modelDetailCard modelDetailNoteCard">
            <span>{isV2 ? "HISTORICAL V2 EVIDENCE" : "HISTORICAL AUDIT"}</span>
            <h2>{isV2 ? "HGB XS + Market historical champion" : "Red-team audit passed"}</h2>
            {isV2 ? (
              <>
                <p>Historical V2 summary: median PR-AUC delta +2.39%, median ROC-AUC 0.5244, and median Q5−Q1 +5.12% across six development folds.</p>
                <p>The full interactive V2 fold chart remains available on Overview under Past Model Evidence.</p>
              </>
            ) : (
              <>
                <p>Preferred historical metric: mean daily common-support Spearman RankIC {V4X_ALPHA.auditedCommonSupportConsensusIc.toFixed(4)} across {V4X_ALPHA.historicalValidationSessions} chronological validation sessions. The stricter exact-feature-window support audit retained {(V4X_ALPHA.auditedStrictSupportRetainedFraction * 100).toFixed(1)}% of observable rows and still produced RankIC {V4X_ALPHA.auditedStrictSupportConsensusIc.toFixed(4)}.</p>
                <p>Geometry3 added about +{V4X_ALPHA.auditedCommonSupportIncrementalIc.toFixed(4)} mean daily consensus RankIC versus the same 25-feature V4 control; paired fold delta was positive in {V4X_ALPHA.auditedPositivePairedConsensusDeltaFolds}/{V4X_ALPHA.foldCount} folds. No critical historical leakage or metric error was found. These remain historical-development results, not X1 prospective performance.</p>
                <p>V4-X is frozen. New sessions only create scores; the model is not retrained, retuned, or historically re-evaluated during X1, and realized forward performance stays hidden until the frozen outcome gate opens.</p>
              </>
            )}
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
          ) : <div className="modelDetailEmpty">No forward score artifact has been produced for this model yet.</div>}
          {error && <div className="modelDetailError">{error}</div>}
        </section>
      </div>
    </main>
  );
}
