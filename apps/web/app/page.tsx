"use client";

import { useEffect, useMemo, useState } from "react";
import { V2_CHAMPION } from "@/lib/model-catalog";
import { V4X_ALPHA, V4X_CONSENSUS_FOLDS } from "@/lib/v4x-catalog";

type OverviewRuntimeStatus = {
  data_ready_sessions: number;
  next_missing_session: string | null;
  model_runs: Array<{
    session_date: string;
    model_id: string;
    state: string;
    artifact_sha256?: string | null;
  }>;
  outcome_access: "LOCKED";
};

type OverviewStatusResponse = {
  status?: OverviewRuntimeStatus;
};

function Logo() {
  return <div className="brandMark" aria-hidden="true"><span /><span /><span /><span /></div>;
}

function pct(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

function ic(value: number) {
  return value.toFixed(3);
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

function HistoricalIcChart() {
  const width = 760;
  const height = 300;
  const left = 58;
  const right = 24;
  const top = 28;
  const bottom = 42;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const maxIc = 0.18;
  const minIc = 0;
  const x = (index: number) => left + (index / (V4X_CONSENSUS_FOLDS.length - 1)) * chartWidth;
  const y = (value: number) => top + ((maxIc - value) / (maxIc - minIc)) * chartHeight;
  const geometryPath = V4X_CONSENSUS_FOLDS.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.geometry3)}`).join(" ");
  const controlPath = V4X_CONSENSUS_FOLDS.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.control)}`).join(" ");
  const guides = [0, 0.05, 0.10, 0.15];

  return (
    <div className="chartWrap editorialChart">
      <div className="evidenceChartMeta">
        <div className="evidenceChartLabel"><span>Consensus daily rank IC</span></div>
        <div className="evidenceChartLegend">
          <small><i className="seriesMarker" style={{ background: "#216b8c" }} />V4-X Geometry3</small>
          <small><i className="seriesMarker" style={{ background: "#a56812" }} />Context25 control</small>
        </div>
      </div>
      <svg className="foldSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Historical consensus rank IC by fold for V4-X Geometry3 and Context25 control">
        {guides.map((value) => (
          <g key={value}>
            <line className={`gridLine ${value === 0 ? "zeroLine" : ""}`} x1={left} x2={width - right} y1={y(value)} y2={y(value)} />
            <text className="axisLabel" x={left - 12} y={y(value) + 4} textAnchor="end">{value.toFixed(2)}</text>
          </g>
        ))}
        <path className="linePath" d={controlPath} style={{ stroke: "#a56812" }} />
        <path className="linePath" d={geometryPath} style={{ stroke: "#216b8c" }} />
        {V4X_CONSENSUS_FOLDS.map((point, index) => (
          <g key={point.fold}>
            <circle cx={x(index)} cy={y(point.control)} r="4.5" fill="white" stroke="#a56812" strokeWidth="2" />
            <circle cx={x(index)} cy={y(point.geometry3)} r="5" fill="white" stroke="#216b8c" strokeWidth="2" />
            <text className="foldAxis" x={x(index)} y={height - 14} textAnchor="middle">{point.fold}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function Home() {
  const [forwardStatus, setForwardStatus] = useState<OverviewRuntimeStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetch("/api/monitor/status", { cache: "no-store" })
        .then((response) => response.json() as Promise<OverviewStatusResponse>)
        .then((payload) => { if (!cancelled) setForwardStatus(payload.status ?? null); })
        .catch(() => { if (!cancelled) setForwardStatus(null); })
        .finally(() => { if (!cancelled) setLoading(false); });
    };
    load();
    const timer = window.setInterval(load, 5_000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  const v4xSessions = useMemo(() => new Set(
    (forwardStatus?.model_runs ?? [])
      .filter((run) => run.model_id === V4X_ALPHA.id && run.state === "DONE" && Boolean(run.artifact_sha256))
      .map((run) => run.session_date),
  ), [forwardStatus]);

  const v2Sessions = useMemo(() => new Set(
    (forwardStatus?.model_runs ?? [])
      .filter((run) => run.model_id === V2_CHAMPION.id && run.state === "DONE" && Boolean(run.artifact_sha256))
      .map((run) => run.session_date),
  ), [forwardStatus]);

  const sharedSessions = [...v4xSessions].filter((date) => v2Sessions.has(date)).length;

  return (
    <main className="appShell editorialShell">
      <header className="topNav editorialNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a className="active" href="/#overview">Overview</a>
            <a href="/monitoring">Forward Monitoring</a>
          </nav>
        </div>
      </header>

      <div className="page overviewPage" id="top">
        <section className="overviewHero" id="overview">
          <div>
            <p className="overviewKicker">CURRENT ALPHA</p>
            <h1>V4-X Geometry3</h1>
            <p className="overviewLead">Historical rank-alpha evidence is strong. The model family is frozen and now moves into a clean 100-session forward confirmation, with V2 retained as the long-running reference.</p>
          </div>
          <div className="overviewStatus">
            <span className="overviewStatusDot" />
            <span>V4-X1 / FROZEN</span>
            <strong>Forward confirmation</strong>
          </div>
        </section>

        <section className="overviewStats" aria-label="Current alpha summary">
          <article><span>HISTORICAL CONSENSUS IC</span><strong className="positiveText">{ic(V4X_ALPHA.historicalConsensusIc)}</strong><small>Geometry3 · V4-3R evidence</small></article>
          <article><span>CONTEXT25 CONTROL</span><strong>{ic(V4X_ALPHA.historicalControlConsensusIc)}</strong><small>same historical evaluation</small></article>
          <article><span>RELATIVE IC LIFT</span><strong className="positiveText">+{pct(V4X_ALPHA.historicalConsensusRelativeLift)}</strong><small>Geometry3 vs control</small></article>
          <article><span>FORWARD V4-X</span><strong>{loading ? "—" : `${v4xSessions.size} / ${V4X_ALPHA.forwardTargetSessions}`}</strong><small>outcome vault locked</small></article>
        </section>

        <section className="overviewGrid">
          <article className="overviewCard overviewEvidenceCard">
            <div className="overviewCardHead">
              <div><span>HISTORICAL RANK SIGNAL</span><h2>Geometry3 improved the control</h2></div>
              <strong className="overviewEvidenceStatus status-final">6 / 6 POSITIVE</strong>
            </div>
            <p className="overviewCardLead">Consensus rank IC by frozen historical fold. The chart shows the V4-X Geometry3 architecture against its Context25 control; it is historical development evidence, not X1 forward performance.</p>
            <HistoricalIcChart />
            <div className="overviewEvidenceFindings">
              <span>Key evidence</span>
              <ul>
                <li>Median consensus IC: {ic(V4X_ALPHA.historicalControlConsensusIc)} → {ic(V4X_ALPHA.historicalConsensusIc)} ({`+${pct(V4X_ALPHA.historicalConsensusRelativeLift)}`}).</li>
                <li>H5 median IC {ic(V4X_ALPHA.historicalH5Ic)} and H10 median IC {ic(V4X_ALPHA.historicalH10Ic)} for Geometry3.</li>
                <li>Incremental bootstrap IC-delta interval remained positive: {V4X_ALPHA.incrementalBootstrapLow.toFixed(4)} to {V4X_ALPHA.incrementalBootstrapHigh.toFixed(4)}.</li>
              </ul>
            </div>
          </article>

          <article className="overviewCard overviewModelCard">
            <div className="overviewCardHead">
              <div><span>FINAL ALPHA CANDIDATE</span><h2>{V4X_ALPHA.shortName}</h2></div>
              <span className="overviewBadge challengerBadge">V4-X</span>
            </div>
            <div className="overviewModelIdentity"><strong>{V4X_ALPHA.id}</strong><span>Frozen final refit · prospective performance unknown</span></div>
            <dl className="overviewFacts">
              <div><dt>Features</dt><dd>{V4X_ALPHA.featureCount}</dd></div>
              <div><dt>Added geometry</dt><dd>3 completed-session features</dd></div>
              <div><dt>Model bundle</dt><dd>{V4X_ALPHA.modelBundleManifestSha256.slice(0, 12)}...</dd></div>
              <div><dt>Forward gate</dt><dd>{V4X_ALPHA.forwardTargetSessions} sessions</dd></div>
            </dl>
            <a className="overviewLink" href="/monitoring">Open forward monitoring →</a>
          </article>
        </section>

        <section className="overviewCard overviewArchiveCard">
          <div className="overviewCardHead">
            <div><span>ACTIVE MONITORING</span><h2>V4-X + V2</h2></div>
            <p>The main dashboard now tracks only the current alpha candidate and the durable V2 reference.</p>
          </div>
          <div className="overviewArchive">
            <article className="overviewArchiveItem status-final">
              <div className="overviewArchiveRow">
                <span className="overviewArchiveIndex">01</span><span className="overviewArchiveGeneration">V4-X</span>
                <div><strong>Geometry3</strong><small>{V4X_ALPHA.id}</small></div>
                <span className="overviewArchiveResult">{loading ? "Reading runtime" : `${v4xSessions.size} / ${V4X_ALPHA.forwardTargetSessions} forward`}</span>
                <span className="overviewArchiveStatus">CURRENT</span><span />
              </div>
            </article>
            <article className="overviewArchiveItem status-baseline">
              <div className="overviewArchiveRow">
                <span className="overviewArchiveIndex">02</span><span className="overviewArchiveGeneration">V2</span>
                <div><strong>{V2_CHAMPION.shortName}</strong><small>{V2_CHAMPION.id}</small></div>
                <span className="overviewArchiveResult">{loading ? "Reading runtime" : `${v2Sessions.size} / ${V2_CHAMPION.forwardTargetSessions} forward`}</span>
                <span className="overviewArchiveStatus">REFERENCE</span><span />
              </div>
            </article>
          </div>
          <div className="overviewEvidenceFindings">
            <span>Forward state</span>
            <ul>
              <li>{loading ? "Reading canonical EOD runtime." : `${forwardStatus?.data_ready_sessions ?? 0} canonical EOD session(s) archived.`}</li>
              <li>{sharedSessions} session(s) currently have both V4-X and V2 score artifacts.</li>
              <li>Next canonical session: {loading ? "—" : shortDate(forwardStatus?.next_missing_session ?? null)}.</li>
            </ul>
          </div>
        </section>
      </div>
    </main>
  );
}