"use client";

import { useMemo, useState } from "react";
import {
  RESEARCH_EXPERIMENTS,
  type ResearchExperiment,
  type ResearchComparisonClass,
  type ResearchEvidence,
  type ResearchFoldMetric,
} from "@/lib/model-catalog";

type ComparableExperiment = ResearchExperiment & { evidence: ResearchEvidence };
type ComparisonGroup = {
  key: string;
  label: string;
  experiments: ComparableExperiment[];
};

const comparisonClassLabels: Record<ResearchComparisonClass, string> = {
  V2_BASELINE: "V2 baseline",
  OPEN_FEATURES: "Open-feature models",
  V3_VARIANTS: "V3 variants",
  V4_VARIANTS: "V4 variants",
  RISK: "Risk models",
};

type SecondaryMetric = {
  key: "roc" | "qSpread";
  label: string;
  format: (value: number) => string;
};

const comparableExperiments = RESEARCH_EXPERIMENTS.filter(
  (item): item is ComparableExperiment => Boolean(item.evidence),
);

const comparisonGroups: ComparisonGroup[] = (() => {
  const groups = new Map<string, ComparisonGroup>();
  for (const experiment of comparableExperiments) {
    const key = experiment.evidence.metricLabel;
    const existing = groups.get(key);
    if (existing) {
      existing.experiments.push(experiment);
    } else {
      groups.set(key, { key, label: key, experiments: [experiment] });
    }
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      experiments: [...group.experiments].sort(
        (left, right) => (left.historicalRank ?? 999) - (right.historicalRank ?? 999),
      ),
    }))
    .sort((left, right) => {
      if (left.key === "Paired PR-AUC change vs V3-B") return -1;
      if (right.key === "Paired PR-AUC change vs V3-B") return 1;
      return right.experiments.length - left.experiments.length || left.label.localeCompare(right.label);
    });
})();

const defaultGroup = comparisonGroups.find((group) => group.key === "Paired PR-AUC change vs V3-B") ?? comparisonGroups[0];
const defaultClass = defaultGroup?.experiments[0]?.comparisonClass ?? "V3_VARIANTS";
const baselineExperiment = comparableExperiments.find((experiment) => experiment.generation === "V3-B") ?? null;
const challengerSlotCount = 2;
const secondaryMetrics: readonly SecondaryMetric[] = [
  { key: "roc", label: "ROC-AUC", format: (value) => value.toFixed(4) },
  { key: "qSpread", label: "Q5-Q1 spread", format: (value) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%` },
];

function Logo() {
  return <div className="brandMark" aria-hidden="true"><span /><span /><span /><span /></div>;
}

function experimentKey(item: ResearchExperiment) {
  return `${item.generation}:${item.candidate}`;
}

function firstKeysFor(group: ComparisonGroup | undefined, comparisonClass: ResearchComparisonClass | "") {
  return (group?.experiments ?? [])
    .filter((experiment) => experiment.comparisonClass === comparisonClass)
    .slice(0, challengerSlotCount)
    .map(experimentKey);
}

function statusLabel(status: ResearchExperiment["status"]) {
  if (status === "FINAL") return "FINAL";
  if (status === "BASELINE") return "BASELINE";
  if (status === "FAIL") return "FAILED";
  if (status === "BLOCKED") return "BLOCKED";
  return "UNDER REVIEW";
}

function signedPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function pointFor(series: ComparableExperiment["evidence"]["series"][number], fold: string) {
  return series.points.find((point) => point.fold === fold) ?? null;
}

function allFolds(experiments: readonly (ComparableExperiment | null)[]) {
  const folds = new Set<string>();
  for (const experiment of experiments) {
    for (const series of experiment?.evidence.series ?? []) {
      for (const point of series.points) folds.add(point.fold);
    }
  }
  return [...folds].sort((left, right) => Number(left.slice(1)) - Number(right.slice(1)));
}

function hasMetric(experiment: ComparableExperiment, metric: SecondaryMetric["key"]) {
  return experiment.evidence.series.some((series) => series.points.some((point) => typeof point[metric] === "number"));
}

function metricCells(
  experiment: ComparableExperiment | null,
  fold: string,
  metric: "deltaPr" | SecondaryMetric["key"],
  format: (value: number) => string,
) {
  if (!experiment) return <span className="compareEmptyCell">Not selected</span>;
  return experiment.evidence.series.map((series) => {
    const point = pointFor(series, fold);
    const value = point ? point[metric] : undefined;
    return (
      <div className="compareSeriesValue" key={`${series.label}-${fold}-${metric}`}>
        {experiment.evidence.series.length > 1 && <span>{series.label}</span>}
        <strong className={typeof value === "number" && value >= 0 ? "comparePositive" : "compareNegative"}>
          {typeof value === "number" ? format(value) : "—"}
        </strong>
      </div>
    );
  });
}

function comparisonCells(experiment: ComparableExperiment | null, fold: string, baseline: boolean) {
  if (baseline) {
    const baselineSeries = experiment?.evidence.series ?? [];
    if (baselineSeries.some((series) => typeof pointFor(series, fold)?.score === "number")) {
      return baselineSeries.map((series) => {
        const point = pointFor(series, fold);
        return (
          <div className="compareSeriesValue compareBaselineValue" key={`${series.label}-${fold}-baseline`}>
            {baselineSeries.length > 1 && <span>{series.label}</span>}
            <strong>{typeof point?.score === "number" ? point.score.toFixed(6) : "—"}</strong>
            <small>Baseline reference</small>
          </div>
        );
      });
    }
    return (
      <div className="compareSeriesValue compareBaselineValue">
        <strong>—</strong>
        <small>Absolute score unavailable</small>
      </div>
    );
  }
  if (!experiment) return <span className="compareEmptyCell">Not selected</span>;
  return experiment.evidence.series.map((series) => {
    const point = pointFor(series, fold);
    const delta = point?.deltaPr;
    return (
      <div className="compareSeriesValue" key={`${series.label}-${fold}-comparison`}>
        {experiment.evidence.series.length > 1 && <span>{series.label}</span>}
        <strong className={typeof delta === "number" && delta >= 0 ? "comparePositive" : "compareNegative"}>
          {typeof point?.score === "number" ? point.score.toFixed(6) : "—"}
        </strong>
        <small>{typeof delta === "number" ? `(${signedPercent(delta)})` : "Paired delta unavailable"}</small>
      </div>
    );
  });
}

export default function ComparePage() {
  const [groupKey, setGroupKey] = useState(defaultGroup?.key ?? "");
  const [comparisonClass, setComparisonClass] = useState<ResearchComparisonClass | "">(defaultClass);
  const [selectedKeys, setSelectedKeys] = useState<string[]>(() => [
    ...firstKeysFor(defaultGroup, defaultClass),
    "",
    "",
  ].slice(0, challengerSlotCount));

  const activeGroup = comparisonGroups.find((group) => group.key === groupKey) ?? comparisonGroups[0];
  const classOptions = useMemo(() => {
    const counts = new Map<ResearchComparisonClass, number>();
    for (const experiment of activeGroup?.experiments ?? []) {
      counts.set(experiment.comparisonClass, (counts.get(experiment.comparisonClass) ?? 0) + 1);
    }
    return [...counts.entries()].map(([key, count]) => ({ key, count }));
  }, [activeGroup]);
  const activeClass = classOptions.some((option) => option.key === comparisonClass)
    ? comparisonClass
    : classOptions[0]?.key ?? "";
  const compatibleExperiments = useMemo(
    () => (activeGroup?.experiments ?? []).filter((experiment) => experiment.comparisonClass === activeClass),
    [activeClass, activeGroup],
  );
  const availableByKey = useMemo(
    () => new Map(compatibleExperiments.map((item) => [experimentKey(item), item])),
    [compatibleExperiments],
  );
  const selectedExperiments = selectedKeys.map((key) => availableByKey.get(key) ?? null);
  const comparisonColumns = [baselineExperiment, ...selectedExperiments];
  const folds = allFolds(comparisonColumns);
  const completeSelections = selectedExperiments.filter((item): item is ComparableExperiment => Boolean(item));
  const comparableSecondaryMetrics = secondaryMetrics.filter((metric) =>
    completeSelections.length > 0 && completeSelections.every((experiment) => hasMetric(experiment, metric.key)),
  );

  function changeGroup(nextKey: string) {
    const nextGroup = comparisonGroups.find((group) => group.key === nextKey);
    const nextClass = nextGroup?.experiments[0]?.comparisonClass ?? "";
    setGroupKey(nextKey);
    setComparisonClass(nextClass);
    setSelectedKeys([...firstKeysFor(nextGroup, nextClass), "", ""].slice(0, challengerSlotCount));
  }

  function changeComparisonClass(nextClass: ResearchComparisonClass) {
    setComparisonClass(nextClass);
    setSelectedKeys([...firstKeysFor(activeGroup, nextClass), "", ""].slice(0, challengerSlotCount));
  }

  function changeSlot(slot: number, value: string) {
    setSelectedKeys((current) => current.map((key, index) => index === slot ? value : key));
  }

  return (
    <main className="appShell editorialShell compareShell">
      <header className="topNav editorialNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a href="/#overview">Overview</a>
            <a href="/monitoring">Forward Monitoring</a>
            <a className="active" href="/compare">Compare</a>
          </nav>
        </div>
      </header>

      <div className="page comparePage">
        <section className="compareHero">
          <div>
            <p className="overviewKicker">HISTORICAL EVIDENCE</p>
            <h1>Compare models</h1>
            <p className="compareLead">Compare F1-F6 results side by side without mixing incompatible measurement contracts.</p>
          </div>
          <a className="compareBackLink" href="/#research-lineage">Back to research archive -&gt;</a>
        </section>

        <section className="surface compareControls">
          <div className="compareControlIntro">
            <div><span>COMPARISON CONTRACT</span><h2>Choose one metric family</h2></div>
            <p>The benchmark and primary metric are part of the evidence contract. Models from different contracts stay in separate views.</p>
          </div>
          <div className="compareGroupSelectors">
            <label className="compareGroupSelect">
              <span>Metric family</span>
              <select value={activeGroup?.key ?? ""} onChange={(event) => changeGroup(event.target.value)}>
                {comparisonGroups.map((group) => <option value={group.key} key={group.key}>{group.label} ({group.experiments.length})</option>)}
              </select>
            </label>
            <label className="compareGroupSelect">
              <span>Model class</span>
              <select value={activeClass} onChange={(event) => changeComparisonClass(event.target.value as ResearchComparisonClass)}>
                {classOptions.map(({ key, count }) => <option value={key} key={key}>{comparisonClassLabels[key]} ({count})</option>)}
              </select>
            </label>
          </div>
          <div className="compareModelSelectors" aria-label="Choose up to two challenger models">
            {selectedKeys.map((selectedKey, slot) => (
              <label className="compareModelSelector" key={`slot-${slot}`}>
                <span>Challenger {slot + 1}</span>
                <select value={selectedKey} onChange={(event) => changeSlot(slot, event.target.value)}>
                  <option value="">Choose model</option>
                  {compatibleExperiments.map((experiment) => {
                    const key = experimentKey(experiment);
                    const usedElsewhere = selectedKeys.some((otherKey, otherSlot) => otherSlot !== slot && otherKey === key);
                    return <option value={key} key={key} disabled={usedElsewhere}>{experiment.generation} / {experiment.name}</option>;
                  })}
                </select>
              </label>
            ))}
          </div>
          <div className="compareContractNote"><i /> V3-B is the fixed baseline. Showing {completeSelections.length} of {challengerSlotCount} challenger slots; missing folds remain blank.</div>
        </section>

        <section className="surface compareTablePanel">
          <div className="comparePanelHead">
            <div><span>FOLD-BY-FOLD VIEW</span><h2>{activeGroup?.label ?? "No metric family"}</h2></div>
            <span className="compareFoldCount">{folds.length ? `${folds[0]}-${folds[folds.length - 1]}` : "No folds"}</span>
          </div>
          <div className="compareNormalizationNote">
            <strong>Comparison basis</strong>
            <p>
              V3-B stays fixed on the left as the incumbent baseline. Each challenger cell is formatted as absolute score plus paired delta when those values are certified.
              {selectedExperiments.some((experiment) => experiment?.generation === "O2") && " O2 support-normalized absolute scores are not present in the current catalog; missing rows are not imputed or reweighted here."}
            </p>
          </div>
          <div className="compareTableScroll">
            <div className="compareTable">
              <div className="compareTableHeader compareFoldHeader">FOLD</div>
              {comparisonColumns.map((experiment, index) => (
                <div className="compareTableHeader compareModelHeader" key={`header-${index}`}>
                  {experiment ? (
                    <><span>{index === 0 ? "V3-B / BASELINE" : `${experiment.generation} / ${statusLabel(experiment.status)}`}</span><strong>{experiment.name}</strong><small>{experiment.candidate}</small></>
                  ) : <span>Choose model</span>}
                </div>
              ))}

              {folds.map((fold) => (
                <div className="compareTableRow" key={fold}>
                  <div className="compareFoldCell">{fold}</div>
                  {comparisonColumns.map((experiment, index) => (
                    <div className="compareMetricCell" key={`${fold}-${index}`}>
                      {comparisonCells(experiment, fold, index === 0)}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="compareSecondaryGrid">
          <article className="surface compareInfoCard">
            <span>WHY THIS IS FAIR</span>
            <h2>Same contract, same rows</h2>
            <ul>
              <li>One table means the same primary metric label and benchmark.</li>
              <li>F1-F6 are chronological development folds, not fresh-forward outcomes.</li>
              <li>Multi-variant candidates remain separate inside their model column.</li>
            </ul>
          </article>
          <article className="surface compareInfoCard">
            <span>METRIC AVAILABILITY</span>
            <h2>Secondary metrics stay separate</h2>
            {comparableSecondaryMetrics.length ? (
              <div className="compareSecondaryList">
                {comparableSecondaryMetrics.map((metric) => <span key={metric.key}>{metric.label} is available across all selected models.</span>)}
              </div>
            ) : (
              <p>No secondary metric is complete across all selected models in this contract. ROC-AUC and Q5-Q1 values are not mixed into the PR-AUC table.</p>
            )}
          </article>
        </section>

        {comparableSecondaryMetrics.map((metric) => (
          <section className="surface compareTablePanel compareSecondaryPanel" key={metric.key}>
            <div className="comparePanelHead"><div><span>SECONDARY METRIC</span><h2>{metric.label}</h2></div></div>
            <div className="compareTableScroll">
              <div className="compareTable">
                <div className="compareTableHeader compareFoldHeader">FOLD</div>
                {selectedExperiments.map((experiment, index) => <div className="compareTableHeader compareModelHeader" key={`secondary-header-${index}`}>{experiment?.name ?? "Choose model"}</div>)}
                {folds.map((fold) => (
                  <div className="compareTableRow" key={`${metric.key}-${fold}`}>
                    <div className="compareFoldCell">{fold}</div>
                    {selectedExperiments.map((experiment, index) => <div className="compareMetricCell" key={`${metric.key}-${fold}-${index}`}>{metricCells(experiment, fold, metric.key, metric.format)}</div>)}
                  </div>
                ))}
              </div>
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
