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
            <div><span>ΔPR-AUC</span><strong className={styles.positive}>+{pct(activePoint.deltaPr)}</strong></div>
            <div><span>ΔROC</span><strong className={styles.positive}>+{activePoint.roc.toFixed(4)}</strong></div>
            <div><span>ΔQ5−Q1</span><strong className={styles.positive}>+{pct(activePoint.qSpread)}</strong></div>
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

      <div className="page editorialPage" id="top">
        <section className="editorialHero" id="overview">
          <div className="heroTopline"><span>01 / FINAL RANKER</span><span>IDX · OUTCOME-BLIND RESEARCH</span></div>
          <div className="heroDisplay" aria-label="V3-B Structure Lite">
            <span>V3—B</span>
            <span>STRUCTURE</span>
            <span className="heroDisplayAccent">LITE</span>
          </div>
          <div className="heroBottomGrid">
            <p>Frozen cross-sectional opportunity ranker for the independent 100-session forward block.</p>
            <div><span>MODEL</span><strong>{FINAL_RANKER.id}</strong></div>
            <div><span>STATUS</span><strong className="positiveText">FINAL / FROZEN</strong></div>
          </div>
        </section>

        <section className="editorialStats" aria-label="Final model facts">
          <article><span>FEATURES</span><strong>{FINAL_RANKER.featureCount}</strong><small>25 V2 + 8 structure</small></article>
          <article><span>TRAINING ROWS</span><strong>{FINAL_RANKER.finalRefitRows.toLocaleString("en-US")}</strong><small>{FINAL_RANKER.finalRefitTickers} tickers</small></article>
          <article><span>DISCOVERY ΔPR</span><strong className="positiveText">+{pct(FINAL_RANKER.discoveryMedianPairedDeltaPr)}</strong><small>median F1–F4</small></article>
          <article><span>LATE CONFIRMATION</span><strong className="positiveText">+{pct(FINAL_RANKER.lateMedianPairedDeltaPr)}</strong><small>median F5/F6</small></article>
        </section>

        <section className="editorialSection promotionSection">
          <div className="sectionIndex"><span>02</span><p>PROMOTION EVIDENCE</p></div>
          <div className="sectionContent">
            <div className="editorialHeadingRow">
              <h2>WHY<br />IT WON</h2>
              <div className="sectionAside"><span>4 / 4</span><p>paired discovery PR improvements positive</p></div>
            </div>
            <FoldChart folds={V3_B_DISCOVERY_FOLDS} />
            <div className="editorialRuleNote"><span>F1—F4 discovery</span><span>F5—F6 late confirmation</span><span>V2 remains frozen baseline</span></div>
          </div>
        </section>

        <section className="editorialSection forwardEditorial">
          <div className="sectionIndex"><span>03</span><p>FORWARD TEST</p></div>
          <div className="sectionContent forwardEditorialGrid">
            <div>
              <h2>0<span>/100</span></h2>
              <p className="forwardEditorialLead">Scores may accumulate. Outcomes do not.</p>
            </div>
            <div className="forwardEditorialFacts">
              <div><span>ACTIVE MODEL</span><strong>{FINAL_RANKER.shortName}</strong></div>
              <div><span>MODEL SHA</span><strong>{FINAL_RANKER.modelSha256.slice(0, 14)}…</strong></div>
              <div><span>OUTCOME VAULT</span><strong className="negativeText">LOCKED</strong></div>
              <a href="/monitoring">OPEN FORWARD MONITORING ↗</a>
            </div>
          </div>
        </section>

        <section className="editorialSection lineageSection" id="research-lineage">
          <div className="sectionIndex"><span>04</span><p>RESEARCH ARCHIVE</p></div>
          <div className="sectionContent">
            <div className="editorialHeadingRow archiveHeading"><h2>WHAT<br />WE TESTED</h2><p>Every failed candidate stays visible.</p></div>
            <div className="editorialArchive">
              {RESEARCH_EXPERIMENTS.map((item, index) => (
                <article className={`archiveRow status-${item.status.toLowerCase()}`} key={`${item.generation}-${item.candidate}`}>
                  <span className="archiveIndex">{String(index + 1).padStart(2, "0")}</span>
                  <span className="archiveGeneration">{item.generation}</span>
                  <div className="archiveName"><strong>{item.name}</strong><small>{item.candidate}</small></div>
                  <span className="archiveResult">{item.result}</span>
                  <span className="archiveStatus">{statusLabel(item.status)}</span>
                </article>
              ))}
            </div>
          </div>
        </section>

        <footer className="editorialFooter"><span>IDX TRADE / RESEARCH ONLY</span><span>OUTCOMES REMAIN SEALED</span></footer>
      </div>
    </main>
  );
}
