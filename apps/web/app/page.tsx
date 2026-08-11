"use client";

import { useEffect, useRef, useState } from "react";
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

type OverviewRuntimeStatus = {
  model_runs: Array<{
    session_date: string;
    model_id: string;
    state: string;
    artifact_sha256?: string | null;
  }>;
};

type OverviewStatusResponse = {
  status?: OverviewRuntimeStatus;
};

type ArchiveSort = "best" | "latest" | "name";
type ArchiveStatusFilter = "all" | "passed" | "not-passed";
type ArchiveModelFilter = "all" | string;

const archiveStatusPriority: Record<ResearchStatus, number> = {
  FINAL: 0,
  BASELINE: 1,
  RESEARCH: 2,
  BLOCKED: 3,
  FAIL: 4,
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

function decisionVerb(status: ResearchStatus) {
  if (status === "FINAL" || status === "BASELINE") return "passed";
  if (status === "BLOCKED") return "blocked";
  if (status === "FAIL") return "failed";
  return "under review";
}

function experimentKey(item: (typeof RESEARCH_EXPERIMENTS)[number]) {
  return `${item.generation}:${item.candidate}`;
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

function ModelEvidencePicker({
  items,
  value,
  onChange,
}: {
  items: readonly (typeof RESEARCH_EXPERIMENTS)[number][];
  value: string;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = items.find((item) => experimentKey(item) === value) ?? items[0];
  const versionOrder = ["V1", "V2", "V3", "V4", "Risk"];
  const versions = versionOrder.filter((version) => items.some((item) => {
    const group = item.generation.startsWith("V") ? item.generation.split("-")[0] : item.generation;
    return group === version;
  }));

  useEffect(() => {
    if (!open) return;
    const handleOutsideClick = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [open]);

  return (
    <div className="modelEvidencePicker" ref={rootRef}>
      <button className="modelEvidencePickerTrigger" type="button" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span>{selected.generation} · {selected.name}</span><b aria-hidden="true">⌄</b>
      </button>
      {open && (
        <div className="modelEvidencePickerMenu" role="listbox" aria-label="Models grouped by version">
          {versions.map((version) => (
            <div className="modelPickerGroup" key={version}>
              <div className="modelPickerGroupLabel">{version}</div>
              {items.filter((item) => {
                const group = item.generation.startsWith("V") ? item.generation.split("-")[0] : item.generation;
                return group === version;
              }).map((item) => {
                const statusClass = item.status.toLowerCase();
                const isSelected = experimentKey(item) === value;
                return (
                  <button
                    className={`modelPickerOption ${isSelected ? "isSelected" : ""}`}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    key={experimentKey(item)}
                    onClick={() => { onChange(experimentKey(item)); setOpen(false); }}
                  >
                    <i className={`modelPickerDot ${statusClass}`} aria-hidden="true" />
                    <span>{item.name}</span>
                    <small>{statusLabel(item.status)}</small>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [forwardStatus, setForwardStatus] = useState<OverviewRuntimeStatus | null>(null);
  const [forwardStatusLoading, setForwardStatusLoading] = useState(true);
  const [archiveSort, setArchiveSort] = useState<ArchiveSort>("best");
  const [archiveStatusFilter, setArchiveStatusFilter] = useState<ArchiveStatusFilter>("all");
  const [archiveModelFilter, setArchiveModelFilter] = useState<ArchiveModelFilter>("all");
  const [expandedArchiveKey, setExpandedArchiveKey] = useState<string | null>(null);
  const [selectedModelKey, setSelectedModelKey] = useState(experimentKey(RESEARCH_EXPERIMENTS[2]));

  useEffect(() => {
    let cancelled = false;
    fetch("/api/monitor/status", { cache: "no-store" })
      .then((response) => response.json() as Promise<OverviewStatusResponse>)
      .then((payload) => {
        if (!cancelled) setForwardStatus(payload.status ?? null);
      })
      .catch(() => {
        if (!cancelled) setForwardStatus(null);
      })
      .finally(() => {
        if (!cancelled) setForwardStatusLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const visibleExperiments = [...RESEARCH_EXPERIMENTS]
    .filter((item) => {
      const passed = item.status === "FINAL" || item.status === "BASELINE";
      const matchesStatus = archiveStatusFilter === "all"
        || (archiveStatusFilter === "passed" && passed)
        || (archiveStatusFilter === "not-passed" && !passed);
      const modelKey = experimentKey(item);
      const matchesModel = archiveModelFilter === "all" || modelKey === archiveModelFilter;
      return matchesStatus && matchesModel;
    })
    .sort((left, right) => {
      if (archiveSort === "name") return left.name.localeCompare(right.name);
      if (archiveSort === "latest") {
        return RESEARCH_EXPERIMENTS.indexOf(right) - RESEARCH_EXPERIMENTS.indexOf(left);
      }
      return archiveStatusPriority[left.status] - archiveStatusPriority[right.status]
        || RESEARCH_EXPERIMENTS.indexOf(left) - RESEARCH_EXPERIMENTS.indexOf(right);
    });
  const selectedExperiment = RESEARCH_EXPERIMENTS.find((item) => experimentKey(item) === selectedModelKey) ?? RESEARCH_EXPERIMENTS[0];
  const finalScoredSessions = new Set(
    (forwardStatus?.model_runs ?? [])
      .filter((run) => run.model_id === FINAL_RANKER.id && run.state === "DONE" && Boolean(run.artifact_sha256))
      .map((run) => run.session_date),
  ).size;

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
          <p className="overviewKicker">MODEL OVERVIEW</p>
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
          <article><span>FORWARD BLOCK</span><strong>{forwardStatusLoading ? "—" : `${finalScoredSessions} / ${FINAL_RANKER.forwardTargetSessions}`}</strong><small>{forwardStatusLoading ? "reading runtime" : "verified score artifacts"}</small></article>
        </section>

        <section className="overviewGrid">
          <article className="overviewCard overviewEvidenceCard">
            <div className="overviewCardHead">
              <div><span>MODEL EVIDENCE</span><h2>Why {selectedExperiment.generation} {decisionVerb(selectedExperiment.status)}?</h2></div>
              <strong className={`overviewEvidenceStatus status-${selectedExperiment.status.toLowerCase()}`}>{statusLabel(selectedExperiment.status)}</strong>
            </div>
            <div className="overviewEvidenceSelector">
              <span>Inspect model</span>
              <ModelEvidencePicker items={RESEARCH_EXPERIMENTS} value={selectedModelKey} onChange={setSelectedModelKey} />
            </div>
            {selectedExperiment.generation === "V3-B" ? (
              <>
                <p className="overviewCardLead">Paired discovery PR-AUC improved across every F1-F4 fold.</p>
                <FoldChart folds={V3_B_DISCOVERY_FOLDS} />
              </>
            ) : (
              <div className={`overviewDecisionGraphic status-${selectedExperiment.status.toLowerCase()}`}>
                <div className="overviewDecisionTrack"><span>Candidate</span><i>→</i><span>Evidence review</span><i>→</i><strong>{statusLabel(selectedExperiment.status)}</strong></div>
                <p>{selectedExperiment.result}</p>
              </div>
            )}
            <div className="overviewEvidenceReason"><span>Decision rationale</span><p>{selectedExperiment.note}</p></div>
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
            <p>Browse tested candidates by result, model, or ranking.</p>
          </div>
          <div className="overviewArchiveToolbar" aria-label="Research archive filters">
            <label>
              <span>Ranking</span>
              <select value={archiveSort} onChange={(event) => setArchiveSort(event.target.value as ArchiveSort)}>
                <option value="best">Best → worst</option>
                <option value="latest">Latest tested</option>
                <option value="name">Name A-Z</option>
              </select>
            </label>
            <label>
              <span>Result</span>
              <select value={archiveStatusFilter} onChange={(event) => setArchiveStatusFilter(event.target.value as ArchiveStatusFilter)}>
                <option value="all">All results</option>
                <option value="passed">Passed</option>
                <option value="not-passed">Not passed</option>
              </select>
            </label>
            <label>
              <span>Model</span>
              <select value={archiveModelFilter} onChange={(event) => setArchiveModelFilter(event.target.value)}>
                <option value="all">All models</option>
                {RESEARCH_EXPERIMENTS.map((item) => (
                  <option key={experimentKey(item)} value={experimentKey(item)}>
                    {item.generation} · {item.name}
                  </option>
                ))}
              </select>
            </label>
            <span className="overviewArchiveCount">{visibleExperiments.length} / {RESEARCH_EXPERIMENTS.length} tested</span>
          </div>
          <div className="overviewArchive">
            {visibleExperiments.length ? visibleExperiments.map((item, index) => {
              const key = experimentKey(item);
              const expanded = expandedArchiveKey === key;
              return (
                <article className={`overviewArchiveItem status-${item.status.toLowerCase()}`} key={key}>
                  <button
                    type="button"
                    className="overviewArchiveRow"
                    aria-expanded={expanded}
                    aria-label={`${item.name}: view performance and decision reason`}
                    onClick={() => {
                      setSelectedModelKey(key);
                      setExpandedArchiveKey(expanded ? null : key);
                    }}
                  >
                    <span className="overviewArchiveIndex">{String(index + 1).padStart(2, "0")}</span>
                    <span className="overviewArchiveGeneration">{item.generation}</span>
                    <div><strong>{item.name}</strong><small>{item.candidate}</small></div>
                    <span className="overviewArchiveResult">{item.result}</span>
                    <span className="overviewArchiveStatus">{statusLabel(item.status)}</span>
                    <span className="overviewArchiveChevron" aria-hidden="true">{expanded ? "−" : "+"}</span>
                  </button>
                  {expanded && (
                    <div className="overviewArchiveDetail">
                      <div><span>Decision</span><strong>{item.result}</strong></div>
                      <div><span>Why</span><p>{item.note}</p></div>
                    </div>
                  )}
                </article>
              );
            }) : <div className="overviewArchiveEmpty">No tested models match these filters.</div>}
          </div>
        </section>
      </div>
    </main>
  );
}
