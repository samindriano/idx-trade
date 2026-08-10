"use client";

import { useState } from "react";
import styles from "./model-monitor.module.css";
import {
  FINAL_RANKER,
  RESEARCH_EXPERIMENTS,
  V3_B_DISCOVERY_FOLDS,
  type ResearchStatus,
} from "@/lib/model-catalog";

type FoldMetric = {
  fold: string;
  deltaPr: number;
  roc: number;
  qSpread: number;
};

function pct(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`;
}

function Logo() {
  return (
    <div className="brandMark" aria-hidden="true">
      <span /><span /><span /><span />
    </div>
  );
}

function statusLabel(status: ResearchStatus) {
  if (status === "FINAL") return "Final ranker";
  if (status === "BASELINE") return "Baseline";
  if (status === "FAIL") return "Failed";
  if (status === "BLOCKED") return "Blocked";
  return "Research";
}

function statusClass(status: ResearchStatus) {
  if (status === "FINAL") return "championLabel";
  if (status === "BLOCKED") return "statusBadge amber";
  return "statusBadge";
}

function FoldChart({ folds }: { folds: readonly FoldMetric[] }) {
  const [hovered, setHovered] = useState<number | null>(null);
  const width = 760;
  const height = 270;
  const left = 48;
  const right = 22;
  const top = 28;
  const bottom = 42;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const maxY = 0.01;

  const points = folds.map((fold, index) => {
    const x = left + (index / (folds.length - 1)) * chartWidth;
    const y = top + chartHeight - (fold.deltaPr / maxY) * chartHeight;
    return { ...fold, x, y };
  });

  const linePath = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ");
  const areaPath = `${linePath} L${points[points.length - 1].x},${top + chartHeight} L${points[0].x},${top + chartHeight} Z`;
  const gridValues = [0, 0.0025, 0.005, 0.0075, 0.01];
  const activePoint = hovered === null ? null : points[hovered];

  return (
    <div className={`chartWrap ${styles.chartStage}`} onMouseLeave={() => setHovered(null)}>
      <svg className="foldSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="V3-B paired delta PR-AUC versus the V2 control across discovery folds">
        <defs>
          <linearGradient id="area-v3b" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0b8f62" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#0b8f62" stopOpacity="0" />
          </linearGradient>
        </defs>
        {gridValues.map((value) => {
          const y = top + chartHeight - (value / maxY) * chartHeight;
          return (
            <g key={value}>
              <line className="gridLine" x1={left} x2={width - right} y1={y} y2={y} />
              <text className="axisLabel" x={left - 12} y={y + 4} textAnchor="end">{pct(value, 2)}</text>
            </g>
          );
        })}
        <path className="areaPath" d={areaPath} fill="url(#area-v3b)" />
        <path className="linePath" d={linePath} />
        {points.map((point, index) => (
          <g className="chartPoint" key={point.fold} onMouseEnter={() => setHovered(index)}>
            <circle cx={point.x} cy={point.y} r={hovered === index ? 6 : 5} />
            <text className="pointValue" x={point.x} y={point.y - 13} textAnchor="middle">+{pct(point.deltaPr)}</text>
            <text className="foldAxis" x={point.x} y={height - 14} textAnchor="middle">{point.fold}</text>
          </g>
        ))}
      </svg>

      {activePoint && (
        <div
          className={`${styles.tooltip} ${activePoint.x > width * 0.7 ? styles.tooltipLeft : ""}`}
          style={{ left: `${(activePoint.x / width) * 100}%`, top: `${(activePoint.y / height) * 100}%` }}
        >
          <div className={styles.tooltipHead}>
            <strong>{activePoint.fold}</strong>
            <span>V3-B vs V2</span>
          </div>
          <div className={styles.tooltipRows}>
            <div><span>Paired ΔPR</span><strong className={styles.positive}>+{pct(activePoint.deltaPr)}</strong></div>
            <div><span>Paired ΔROC</span><strong className={styles.positive}>+{activePoint.roc.toFixed(4)}</strong></div>
            <div><span>Paired ΔQ5−Q1</span><strong className={styles.positive}>+{pct(activePoint.qSpread)}</strong></div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  return (
    <main className="appShell">
      <header className="topNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a className="active" href="/#overview">Overview</a>
            <a href="/monitoring">Forward Monitoring</a>
          </nav>
          <div className="researchPill"><span className="liveDot" /> Research only</div>
        </div>
      </header>

      <div className="page" id="top">
        <section className="hero" id="overview">
          <div>
            <p className="eyebrow">FINAL ALPHA RANKER</p>
            <h1>V3-B Structure-Lite</h1>
            <p className="heroCopy">The historical alpha search is closed. V3-B is the frozen opportunity ranker that will accumulate outcome-blind forward scores while the independent 100-session validation block matures.</p>
          </div>
          <div className="lockBadge"><span className="lockDot" /> Forward outcomes locked</div>
        </section>

        <section className="modelToolbar">
          <div className="modelSummary">
            <span className="modelBadge champion">FINAL V3</span>
            <div>
              <strong>{FINAL_RANKER.id}</strong>
              <p>V2 market/cross-sectional information + 8 causal Structure-Lite geometry features.</p>
            </div>
          </div>
          <div className="modelSummary">
            <span className="modelBadge">REFIT</span>
            <div>
              <strong>{FINAL_RANKER.finalRefitRows.toLocaleString("en-US")} rows · {FINAL_RANKER.finalRefitTickers} tickers</strong>
              <p>Sessions {FINAL_RANKER.finalRefitSessions}. Training-only final refit; no new historical validation slice.</p>
            </div>
          </div>
        </section>

        <section className="metricStrip">
          <article><span>Discovery paired ΔPR</span><strong className="primaryValue">+{pct(FINAL_RANKER.discoveryMedianPairedDeltaPr)}</strong><small>median F1–F4 vs V2 control</small></article>
          <article><span>Late confirmation ΔPR</span><strong className="primaryValue">+{pct(FINAL_RANKER.lateMedianPairedDeltaPr)}</strong><small>median F5/F6; worst +{pct(FINAL_RANKER.lateWorstPairedDeltaPr)}</small></article>
          <article><span>Frozen feature set</span><strong>{FINAL_RANKER.featureCount}</strong><small>25 V2 + 8 Structure-Lite</small></article>
          <article><span>Evaluated alpha candidates</span><strong>17</strong><small>failed candidates remain in denominator</small></article>
        </section>

        <section className="mainGrid">
          <article className="surface chartPanel">
            <div className="sectionHead">
              <div><span>PROMOTION EVIDENCE</span><h2>V3-B paired uplift vs V2</h2></div>
              <div className="legend"><i /> Δ PR-AUC</div>
            </div>
            <FoldChart folds={V3_B_DISCOVERY_FOLDS} />
            <div className="chartNote">
              <span>Discovery folds only; F5/F6 were a separate one-shot late-development confirmation.</span>
              <span>4 / 4 paired PR improvements positive</span>
            </div>
          </article>

          <article className="surface forwardPanel">
            <div className="sectionHead compact">
              <div><span>INDEPENDENT FORWARD TEST</span><h2>Final V3-B</h2></div>
              <span className="statusBadge amber">PROTECTED</span>
            </div>
            <div className="forwardCount"><strong>0</strong><span>/ {FINAL_RANKER.forwardTargetSessions}</span></div>
            <div className="progressTrack"><span style={{ width: "0%" }} /></div>
            <p className="forwardCopy">Daily scores and ranks may be recorded now. TP/SL outcomes and validation metrics stay hidden until the exact 100-session H10-mature block is complete.</p>
            <div className="forwardFacts">
              <div><span>Active model</span><strong><i className="okDot" /> {FINAL_RANKER.shortName}</strong></div>
              <div><span>Model SHA</span><strong>{FINAL_RANKER.modelSha256.slice(0, 10)}…</strong></div>
              <div><span>Forward cutoff</span><strong>&gt; {FINAL_RANKER.forwardCutoff}</strong></div>
              <div><span>Outcomes</span><strong>Locked</strong></div>
            </div>
            <a className="primaryLink" href="/monitoring">Open forward monitoring →</a>
          </article>
        </section>

        <section className="surface comparisonPanel" id="research-lineage">
          <div className="sectionHead">
            <div><span>RESEARCH LINEAGE</span><h2>What we tested</h2></div>
            <span className="tableHint">Current state · 10 Aug 2026</span>
          </div>
          <div className="tableScroll">
            <table>
              <thead><tr><th>Generation</th><th>Experiment</th><th>Candidate</th><th>Result</th><th>Why it matters</th><th>Status</th></tr></thead>
              <tbody>
                {RESEARCH_EXPERIMENTS.map((item) => (
                  <tr key={`${item.generation}-${item.candidate}`}>
                    <td><span className="generationPill v2">{item.generation}</span></td>
                    <td><strong>{item.name}</strong></td>
                    <td><small>{item.candidate}</small></td>
                    <td>{item.result}</td>
                    <td><small>{item.note}</small></td>
                    <td><span className={statusClass(item.status)}>{statusLabel(item.status)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
