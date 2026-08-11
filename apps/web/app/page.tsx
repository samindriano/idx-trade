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
  return <div className="brandMark" aria-hidden="true"><span /><span /><span /><span /></div>;
}

function statusLabel(status: ResearchStatus) {
  if (status === "FINAL") return "FINAL";
  if (status === "BASELINE") return "BASELINE";
  if (status === "FAIL") return "FAILED";
  if (status === "BLOCKED") return "BLOCKED";
  return "RESEARCH";
}

function FoldChart({ folds }: { folds: readonly FoldMetric[] }) {
  const [hovered, setHovered] = useState<number | null>(null);
  const width = 760;
  const height = 300;
  const left = 54;
  const right = 22;
  const top = 30;
  const bottom = 44;
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
    <div className={`chartWrap editorialChart ${styles.chartStage}`} onMouseLeave={() => setHovered(null)}>
      <svg className="foldSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="V3-B paired delta PR-AUC versus V2 across discovery folds">
        <defs>
          <linearGradient id="area-v3b-editorial" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00a66a" stopOpacity="0.24" />
            <stop offset="100%" stopColor="#00a66a" stopOpacity="0" />
          </linearGradient>
        </defs>
        {gridValues.map((value) => {
          const y = top + chartHeight - (value / maxY) * chartHeight;
          return (
            <g key={value}>
              <line className="gridLine" x1={left} x2={width - right} y1={y} y2={y} />
              <text className="axisLabel" x={left - 12} y={y + 4} textAnchor="end">{pct(value)}</text>
            </g>
          );
        })}
        <path className="areaPath" d={areaPath} fill="url(#area-v3b-editorial)" />
        <path className="linePath" d={linePath} />
        {points.map((point, index) => (
          <g className="chartPoint" key={point.fold} onMouseEnter={() => setHovered(index)}>
            <circle cx={point.x} cy={point.y} r={hovered === index ? 7 : 5} />
            <text className="pointValue" x={point.x} y={point.y - 15} textAnchor="middle">+{pct(point.deltaPr)}</text>
            <text className="foldAxis" x={point.x} y={height - 14} textAnchor="middle">{point.fold}</text>
          </g>
        ))}
      </svg>
      {activePoint && (
        <div className={`${styles.tooltip} ${activePoint.x > width * 0.7 ? styles.tooltipLeft : ""}`} style={{ left: `${(activePoint.x / width) * 100}%`, top: `${(activePoint.y / height) * 100}%` }}>
          <div className={styles.tooltipHead}><strong>{activePoint.fold}</strong><span>V3-B / V2</span></div>
          <div className={styles.tooltipRows}>
            <div><span>Delta PR-AUC</span><strong className={styles.positive}>+{pct(activePoint.deltaPr)}</strong></div>
            <div><span>Delta ROC</span><strong className={styles.positive}>+{activePoint.roc.toFixed(4)}</strong></div>
            <div><span>Delta Q5-Q1</span><strong className={styles.positive}>+{pct(activePoint.qSpread)}</strong></div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  return (
    <main className="appShell editorialShell">
      <header className="topNav editorialNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a className="active" href="/#overview">Overview</a>
            <a href="/monitoring">Forward Monitoring</a>
          </nav>
          <div className="researchPill"><span className="liveDot" /> RESEARCH SYSTEM</div>
        </div>
      </header>

      <div className="page overviewPage" id="top">
        <section className="overviewHero" id="overview">
          <div>
            <p className="overviewKicker">MODEL OVERVIEW / RESEARCH ONLY</p>
            <h1>Research overview</h1>
            <p className="overviewLead">A compact view of the frozen ranker, its promotion evidence, and the forward monitoring lane.</p>
          </div>
          <div className="overviewStatus">
            <span className="overviewStatusDot" />
            <span>V3-B / FINAL</span>
            <strong>Frozen ranker</strong>
          </div>
        </section>

        <section className="overviewStats" aria-label="Final model facts">
          <article><span>ACTIVE MODEL</span><strong>{FINAL_RANKER.shortName}</strong><small>V3-B Structure-Lite</small></article>
          <article><span>FEATURES</span><strong>{FINAL_RANKER.featureCount}</strong><small>25 V2 + 8 structure</small></article>
          <article><span>DISCOVERY DELTA PR</span><strong className="positiveText">+{pct(FINAL_RANKER.discoveryMedianPairedDeltaPr)}</strong><small>median F1-F4</small></article>
          <article><span>FORWARD BLOCK</span><strong>0 / 100</strong><small>scores accumulating</small></article>
        </section>

        <section className="overviewGrid">
          <article className="overviewCard overviewEvidenceCard">
            <div className="overviewCardHead">
              <div><span>PROMOTION EVIDENCE</span><h2>Why V3-B is frozen</h2></div>
              <strong className="overviewEvidenceScore">4 / 4</strong>
            </div>
            <p className="overviewCardLead">Paired discovery PR-AUC improved across every F1-F4 fold.</p>
            <FoldChart folds={V3_B_DISCOVERY_FOLDS} />
            <div className="overviewNote"><span>F1-F4 discovery</span><span>V2 frozen baseline</span></div>
          </article>

          <article className="overviewCard overviewModelCard">
            <div className="overviewCardHead">
              <div><span>ACTIVE MODEL</span><h2>{FINAL_RANKER.shortName}</h2></div>
              <span className="overviewBadge">FINAL</span>
            </div>
            <div className="overviewModelIdentity"><strong>{FINAL_RANKER.id}</strong><span>Outcome-blind scoring</span></div>
            <dl className="overviewFacts">
              <div><dt>Training rows</dt><dd>{FINAL_RANKER.finalRefitRows.toLocaleString("en-US")}</dd></div>
              <div><dt>Universe</dt><dd>{FINAL_RANKER.finalRefitTickers} tickers</dd></div>
              <div><dt>Model SHA</dt><dd>{FINAL_RANKER.modelSha256.slice(0, 12)}...</dd></div>
              <div><dt>Baseline</dt><dd>V2 champion</dd></div>
            </dl>
            <a className="overviewLink" href="/monitoring">Open forward monitoring -&gt;</a>
          </article>
        </section>

        <section className="overviewCard overviewArchiveCard" id="research-lineage">
          <div className="overviewCardHead">
            <div><span>RESEARCH ARCHIVE</span><h2>What we tested</h2></div>
            <p>Failed candidates remain visible for context.</p>
          </div>
          <div className="overviewArchive">
            {RESEARCH_EXPERIMENTS.map((item, index) => (
              <article className={`overviewArchiveRow status-${item.status.toLowerCase()}`} key={`${item.generation}-${item.candidate}`}>
                <span className="overviewArchiveIndex">{String(index + 1).padStart(2, "0")}</span>
                <span className="overviewArchiveGeneration">{item.generation}</span>
                <div><strong>{item.name}</strong><small>{item.candidate}</small></div>
                <span className="overviewArchiveResult">{item.result}</span>
                <span className="overviewArchiveStatus">{statusLabel(item.status)}</span>
              </article>
            ))}
          </div>
        </section>

        <footer className="editorialFooter"><span>IDX TRADE / RESEARCH ONLY</span><span>OUTCOMES REMAIN SEALED</span></footer>
      </div>
    </main>
  );
}
