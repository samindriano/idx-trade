"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./model-monitor.module.css";
import {
  FINAL_RANKER,
  RESEARCH_EXPERIMENTS,
  type ResearchFoldMetric,
  type ResearchEvidenceSeries,
  type ResearchStatus,
} from "@/lib/model-catalog";

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

function signedPct(value: number) {
  return `${value >= 0 ? "+" : ""}${pct(value)}`;
}

const POSITIVE_TONE = "#00a66a";
const NEGATIVE_TONE = "#d84b56";

function metricTone(value: number) {
  return value >= 0 ? POSITIVE_TONE : NEGATIVE_TONE;
}

type PlottedPoint = ResearchFoldMetric & { x: number; y: number };

function lineSegments(points: readonly PlottedPoint[], zeroY: number) {
  return points.slice(0, -1).flatMap((start, index) => {
    const end = points[index + 1];
    const startTone = metricTone(start.deltaPr);
    const endTone = metricTone(end.deltaPr);
    const startsOnSameSide = (start.deltaPr >= 0) === (end.deltaPr >= 0);

    if (startsOnSameSide || start.deltaPr === 0 || end.deltaPr === 0) {
      return [{ d: `M${start.x},${start.y} L${end.x},${end.y}`, color: startTone }];
    }

    const zeroRatio = -start.deltaPr / (end.deltaPr - start.deltaPr);
    const zeroX = start.x + zeroRatio * (end.x - start.x);
    return [
      { d: `M${start.x},${start.y} L${zeroX},${zeroY}`, color: startTone },
      { d: `M${zeroX},${zeroY} L${end.x},${end.y}`, color: endTone },
    ];
  });
}

function areaSegments(points: readonly PlottedPoint[], zeroY: number) {
  return points.slice(0, -1).flatMap((start, index) => {
    const end = points[index + 1];
    const startTone = metricTone(start.deltaPr);
    const endTone = metricTone(end.deltaPr);
    const startsOnSameSide = (start.deltaPr >= 0) === (end.deltaPr >= 0);

    if (startsOnSameSide || start.deltaPr === 0 || end.deltaPr === 0) {
      return [{ d: `M${start.x},${zeroY} L${start.x},${start.y} L${end.x},${end.y} L${end.x},${zeroY} Z`, color: startTone }];
    }

    const zeroRatio = -start.deltaPr / (end.deltaPr - start.deltaPr);
    const zeroX = start.x + zeroRatio * (end.x - start.x);
    return [
      { d: `M${start.x},${zeroY} L${start.x},${start.y} L${zeroX},${zeroY} Z`, color: startTone },
      { d: `M${zeroX},${zeroY} L${end.x},${end.y} L${end.x},${zeroY} Z`, color: endTone },
    ];
  });
}

const FOLD_GUIDE = [
  { fold: "F1", train: "1–504", gap: "505–524", validation: "525–624" },
  { fold: "F2", train: "1–624", gap: "625–644", validation: "645–744" },
  { fold: "F3", train: "1–744", gap: "745–764", validation: "765–864" },
  { fold: "F4", train: "1–864", gap: "865–884", validation: "885–984" },
  { fold: "F5", train: "1–984", gap: "985–1004", validation: "1005–1104" },
  { fold: "F6", train: "1–1104", gap: "1105–1124", validation: "1125–1224" },
] as const;

function EvidenceChart({
  series,
  metricLabel,
}: {
  series: readonly ResearchEvidenceSeries[];
  metricLabel: string;
}) {
  const [hovered, setHovered] = useState<{ series: number; point: number } | null>(null);
  const [foldHelpOpen, setFoldHelpOpen] = useState(false);
  const width = 760;
  const height = 300;
  const left = 58;
  const right = 22;
  const top = 34;
  const bottom = 44;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const values = series.flatMap((line) => line.points.map((point) => point.deltaPr));
  const extent = Math.max(0.005, ...values.map((value) => Math.abs(value))) * 1.15;
  const gridValues = [extent, extent / 2, 0, -extent / 2, -extent];
  const zeroY = top + chartHeight / 2;
  const plottedSeries = series.map((line, seriesIndex) => ({
    ...line,
    points: line.points.map((point, pointIndex) => {
      const x = left + (pointIndex / Math.max(1, line.points.length - 1)) * chartWidth;
      const y = top + chartHeight / 2 - (point.deltaPr / extent) * (chartHeight / 2);
      return { ...point, x, y };
    }),
  }));
  const activePoint = hovered ? plottedSeries[hovered.series]?.points[hovered.point] : null;
  const activeSeries = hovered ? plottedSeries[hovered.series] : null;
  const foldGuide = FOLD_GUIDE.slice(0, Math.max(...series.map((line) => line.points.length)));

  return (
    <div className={`chartWrap editorialChart ${styles.chartStage}`} onMouseLeave={() => setHovered(null)}>
      <div className="evidenceChartMeta">
        <div className="evidenceChartLabel">
          <span>{metricLabel}</span>
          <div className="evidenceHelp">
            <button className="evidenceHelpButton" type="button" aria-label="Explain evaluation folds" aria-expanded={foldHelpOpen} onClick={() => setFoldHelpOpen((current) => !current)}>?</button>
            {foldHelpOpen && (
              <div className="evidenceHelpPopover" role="dialog" aria-label="Evaluation fold explanation">
                <strong>How to read these folds</strong>
                <p>Each fold is a chronological walk-forward check: train on earlier sessions, skip a 20-session purge gap, then evaluate on the next 100 sessions.</p>
                <div className="evidenceHelpTable">
                  {foldGuide.map((fold) => (
                    <div key={fold.fold}><b>{fold.fold}</b><span>train {fold.train}</span><span>gap {fold.gap}</span><span>validation {fold.validation}</span></div>
                  ))}
                </div>
                <small>Positive PR-AUC change means the candidate beat the comparator shown above. These are historical development folds, not fresh-forward outcomes.</small>
              </div>
            )}
          </div>
        </div>
        <div className="evidenceChartLegend">
          {series.map((line) => <small key={line.label}><i className="seriesMarker" />{line.label}</small>)}
          <small><i className="positiveMarker" />Positive</small>
          <small><i className="negativeMarker" />Negative</small>
        </div>
      </div>
      <svg className="foldSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${metricLabel} across evaluation folds`}>
        {gridValues.map((value) => {
          const y = top + chartHeight / 2 - (value / extent) * (chartHeight / 2);
          return (
            <g key={value}>
              <line className={`gridLine ${value === 0 ? "zeroLine" : ""}`} x1={left} x2={width - right} y1={y} y2={y} />
              <text className="axisLabel" x={left - 12} y={y + 4} textAnchor="end">{signedPct(value)}</text>
            </g>
          );
        })}
        {plottedSeries.map((line, seriesIndex) => {
          const segments = lineSegments(line.points, zeroY);
          const fills = areaSegments(line.points, zeroY);
          return (
            <g key={line.label}>
              {series.length === 1 && fills.map((segment, segmentIndex) => <path className="areaPath" key={`area-${segmentIndex}`} d={segment.d} style={{ fill: segment.color }} />)}
              {segments.map((segment, segmentIndex) => <path className="linePath" key={`line-${segmentIndex}`} d={segment.d} style={{ stroke: segment.color }} />)}
              {line.points.map((point, pointIndex) => (
                <g className={`chartPoint ${point.deltaPr >= 0 ? "positive" : "negative"}`} key={point.fold} onMouseEnter={() => setHovered({ series: seriesIndex, point: pointIndex })}>
                  <circle cx={point.x} cy={point.y} r={hovered?.series === seriesIndex && hovered.point === pointIndex ? 7 : 5} style={{ stroke: metricTone(point.deltaPr) }} />
                  {(series.length === 1 || (hovered?.series === seriesIndex && hovered.point === pointIndex)) && (
                    <text className="pointValue" x={point.x} y={point.y - 15} textAnchor="middle" style={{ fill: metricTone(point.deltaPr) }}>{signedPct(point.deltaPr)}</text>
                  )}
                  {seriesIndex === 0 && <text className="foldAxis" x={point.x} y={height - 14} textAnchor="middle">{point.fold}</text>}
                </g>
              ))}
            </g>
          );
        })}
      </svg>
      {activePoint && activeSeries && (
        <div className={`${styles.tooltip} ${activePoint.x > width * 0.7 ? styles.tooltipLeft : ""}`} style={{ left: `${(activePoint.x / width) * 100}%`, top: `${(activePoint.y / height) * 100}%` }}>
          <div className={styles.tooltipHead}><strong>{activePoint.fold}</strong><span>{activeSeries.label}</span></div>
          <div className={styles.tooltipRows}>
            <div><span>Delta PR-AUC</span><strong className={activePoint.deltaPr >= 0 ? styles.positive : styles.negative}>{signedPct(activePoint.deltaPr)}</strong></div>
            {activePoint.roc !== undefined && <div><span>Delta ROC</span><strong className={activePoint.roc >= 0 ? styles.positive : styles.negative}>{signedPct(activePoint.roc)}</strong></div>}
            {activePoint.qSpread !== undefined && <div><span>Delta Q5-Q1</span><strong className={activePoint.qSpread >= 0 ? styles.positive : styles.negative}>{signedPct(activePoint.qSpread)}</strong></div>}
          </div>
        </div>
      )}
    </div>
  );
}

function DiagnosticEvidence({ result, note, status, dataBlocker }: { result: string; note: string; status: ResearchStatus; dataBlocker?: boolean }) {
  return (
    <div className={`overviewDiagnosticGraphic status-${status.toLowerCase()}`}>
      <div className="overviewDiagnosticMark">!</div>
      <div>
        <span>{dataBlocker ? "Data blocker" : "Diagnostic view"}</span>
        <strong>{result}</strong>
        <p>{note}</p>
      </div>
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
            {selectedExperiment.evidence ? (
              <>
                <p className="overviewCardLead">{selectedExperiment.evidence.caption}</p>
                <EvidenceChart
                  metricLabel={selectedExperiment.evidence.metricLabel}
                  series={selectedExperiment.evidence.series}
                />
              </>
            ) : (
              <DiagnosticEvidence result={selectedExperiment.result} note={selectedExperiment.note} status={selectedExperiment.status} dataBlocker={selectedExperiment.dataBlocker} />
            )}
            <div className="overviewEvidenceFindings">
              <span>Key findings</span>
              <ul>
                {selectedExperiment.keyFindings.slice(0, 3).map((finding) => <li key={finding}>{finding}</li>)}
              </ul>
            </div>
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
                    <span className={`overviewArchiveChevron ${expanded ? "isExpanded" : ""}`} aria-hidden="true" />
                  </button>
                  <div className={`overviewArchiveDetailWrap ${expanded ? "isOpen" : ""}`} aria-hidden={!expanded}>
                    <div className="overviewArchiveDetail">
                      <div><span>Decision</span><strong>{item.result}</strong></div>
                      <div><span>Why</span><p>{item.note}</p></div>
                    </div>
                  </div>
                </article>
              );
            }) : <div className="overviewArchiveEmpty">No tested models match these filters.</div>}
          </div>
        </section>
      </div>
    </main>
  );
}
