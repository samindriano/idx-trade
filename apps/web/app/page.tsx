"use client";

import { useMemo, useState } from "react";

type FoldMetric = {
  fold: string;
  deltaPr: number;
  roc: number;
  qSpread: number;
};

type ModelRecord = {
  id: string;
  generation: "V1" | "V2";
  label: string;
  badge: string;
  status: string;
  description: string;
  medianDeltaPr: number;
  medianRoc: number;
  medianQSpread: number;
  positiveDeltaFolds: string;
  folds: FoldMetric[];
};

const models: ModelRecord[] = [
  {
    id: "HGB_XS_MARKET",
    generation: "V2",
    label: "HGB XS + Market",
    badge: "V2 CHAMPION",
    status: "Frozen · forward contract active",
    description: "Cross-sectional stock strength, market state, and stock-vs-market context.",
    medianDeltaPr: 0.02388,
    medianRoc: 0.52441,
    medianQSpread: 0.051196,
    positiveDeltaFolds: "6 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.021677, roc: 0.525558, qSpread: 0.084017 },
      { fold: "F2", deltaPr: 0.028999, roc: 0.523262, qSpread: 0.070311 },
      { fold: "F3", deltaPr: 0.008789, roc: 0.527379, qSpread: 0.038651 },
      { fold: "F4", deltaPr: 0.038295, roc: 0.512827, qSpread: 0.057535 },
      { fold: "F5", deltaPr: 0.026082, roc: 0.530579, qSpread: 0.032179 },
      { fold: "F6", deltaPr: 0.018643, roc: 0.493102, qSpread: 0.044856 },
    ],
  },
  {
    id: "HGB_XS",
    generation: "V2",
    label: "HGB XS",
    badge: "V2",
    status: "Historical candidate",
    description: "Nonlinear HGB on same-date cross-sectional stock features without explicit market context.",
    medianDeltaPr: 0.018482,
    medianRoc: 0.515711,
    medianQSpread: 0.036905,
    positiveDeltaFolds: "6 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.020569, roc: 0.513621, qSpread: 0.03434 },
      { fold: "F2", deltaPr: 0.03865, roc: 0.533146, qSpread: 0.08415 },
      { fold: "F3", deltaPr: 0.023723, roc: 0.516927, qSpread: 0.048323 },
      { fold: "F4", deltaPr: 0.015208, roc: 0.516375, qSpread: 0.037645 },
      { fold: "F5", deltaPr: 0.013105, roc: 0.513975, qSpread: 0.036164 },
      { fold: "F6", deltaPr: 0.016394, roc: 0.515047, qSpread: 0.018103 },
    ],
  },
  {
    id: "LOGISTIC_XS",
    generation: "V2",
    label: "Logistic XS",
    badge: "V2",
    status: "Historical candidate",
    description: "Linear cross-sectional baseline used to isolate the effect of same-date normalization.",
    medianDeltaPr: 0.009372,
    medianRoc: 0.506269,
    medianQSpread: 0.019726,
    positiveDeltaFolds: "6 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.009908, roc: 0.502548, qSpread: 0.029134 },
      { fold: "F2", deltaPr: 0.030582, roc: 0.528439, qSpread: 0.07807 },
      { fold: "F3", deltaPr: 0.010496, roc: 0.511545, qSpread: 0.026872 },
      { fold: "F4", deltaPr: 0.003873, roc: 0.495587, qSpread: -0.000081 },
      { fold: "F5", deltaPr: 0.008835, roc: 0.507063, qSpread: 0.012579 },
      { fold: "F6", deltaPr: 0.003217, roc: 0.505476, qSpread: 0.005455 },
    ],
  },
  {
    id: "PAIRWISE_XS",
    generation: "V2",
    label: "Pairwise Logistic XS",
    badge: "V2",
    status: "Historical candidate",
    description: "Linear same-date pairwise ranking experiment retained as an objective-function diagnostic.",
    medianDeltaPr: 0.01067,
    medianRoc: 0.508343,
    medianQSpread: 0.024926,
    positiveDeltaFolds: "6 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.010404, roc: 0.501659, qSpread: 0.018493 },
      { fold: "F2", deltaPr: 0.027711, roc: 0.525379, qSpread: 0.067298 },
      { fold: "F3", deltaPr: 0.010936, roc: 0.511762, qSpread: 0.031359 },
      { fold: "F4", deltaPr: 0.008887, roc: 0.501757, qSpread: 0.012202 },
      { fold: "F5", deltaPr: 0.015098, roc: 0.516769, qSpread: 0.040615 },
      { fold: "F6", deltaPr: 0.002926, roc: 0.504925, qSpread: 0.003426 },
    ],
  },
  {
    id: "V1_HGB_CONTROL",
    generation: "V1",
    label: "HGB Control",
    badge: "V1 CONTROL",
    status: "Historical control · not champion-eligible",
    description: "Original HGB feature set retained only as the locked V2 comparison control.",
    medianDeltaPr: 0.022348,
    medianRoc: 0.51901,
    medianQSpread: 0.031008,
    positiveDeltaFolds: "6 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.017436, roc: 0.512096, qSpread: 0.020781 },
      { fold: "F2", deltaPr: 0.03315, roc: 0.528622, qSpread: 0.068228 },
      { fold: "F3", deltaPr: 0.000785, roc: 0.485803, qSpread: 0.005463 },
      { fold: "F4", deltaPr: 0.028493, roc: 0.533356, qSpread: 0.023201 },
      { fold: "F5", deltaPr: 0.016653, roc: 0.509485, qSpread: 0.038815 },
      { fold: "F6", deltaPr: 0.02726, roc: 0.525924, qSpread: 0.044931 },
    ],
  },
];

const futureModels = ["Recency", "Regime", "Sector Relative", "True Ranking"];

function pct(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`;
}

function Logo() {
  return (
    <div className="brandMark" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}

function FoldChart({ model }: { model: ModelRecord }) {
  const width = 760;
  const height = 270;
  const left = 48;
  const right = 22;
  const top = 28;
  const bottom = 42;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const maxY = 0.04;

  const points = model.folds.map((fold, index) => {
    const x = left + (index / (model.folds.length - 1)) * chartWidth;
    const y = top + chartHeight - (fold.deltaPr / maxY) * chartHeight;
    return { ...fold, x, y };
  });

  const linePath = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ");
  const areaPath = `${linePath} L${points[points.length - 1].x},${top + chartHeight} L${points[0].x},${top + chartHeight} Z`;
  const gridValues = [0, 0.01, 0.02, 0.03, 0.04];

  return (
    <div className="chartWrap" key={model.id}>
      <svg className="foldSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Chronological delta PR-AUC for ${model.label}`}>
        <defs>
          <linearGradient id={`area-${model.id}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4856d6" stopOpacity="0.17" />
            <stop offset="100%" stopColor="#4856d6" stopOpacity="0" />
          </linearGradient>
        </defs>
        {gridValues.map((value) => {
          const y = top + chartHeight - (value / maxY) * chartHeight;
          return (
            <g key={value}>
              <line className="gridLine" x1={left} x2={width - right} y1={y} y2={y} />
              <text className="axisLabel" x={left - 12} y={y + 4} textAnchor="end">{pct(value, 0)}</text>
            </g>
          );
        })}
        <path className="areaPath" d={areaPath} fill={`url(#area-${model.id})`} />
        <path className="linePath" d={linePath} />
        {points.map((point) => (
          <g className="chartPoint" key={point.fold}>
            <circle cx={point.x} cy={point.y} r="5">
              <title>{`${point.fold}: ΔPR ${pct(point.deltaPr)} · ROC ${point.roc.toFixed(3)} · Q5-Q1 ${pct(point.qSpread)}`}</title>
            </circle>
            <text className="pointValue" x={point.x} y={point.y - 13} textAnchor="middle">{pct(point.deltaPr)}</text>
            <text className="foldAxis" x={point.x} y={height - 14} textAnchor="middle">{point.fold}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function Home() {
  const [modelId, setModelId] = useState("HGB_XS_MARKET");
  const model = models.find((item) => item.id === modelId) ?? models[0];
  const v2Models = models.filter((item) => item.generation === "V2");
  const v1Models = models.filter((item) => item.generation === "V1");

  const comparison = useMemo(
    () => [...models].sort((a, b) => b.medianDeltaPr - a.medianDeltaPr),
    []
  );

  const championForward = model.id === "HGB_XS_MARKET";

  return (
    <main className="appShell">
      <header className="topNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home">
            <Logo />
            <span>IDX Trade</span>
          </a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a className="active" href="/#overview">Overview</a>
            <a href="/#models">Models</a>
            <a href="/monitoring">Forward Monitoring</a>
          </nav>
          <div className="researchPill"><span className="liveDot" /> Research only</div>
        </div>
      </header>

      <div className="page" id="top">
        <section className="hero" id="overview">
          <div>
            <p className="eyebrow">MODEL OBSERVATORY</p>
            <h1>Model Monitor</h1>
            <p className="heroCopy">Historical model evidence, comparison, and the frozen V2 champion contract.</p>
          </div>
          <div className="lockBadge"><span className="lockDot" /> Forward outcomes locked</div>
        </section>

        <section className="modelToolbar">
          <div className="modelSelectBlock">
            <label htmlFor="model-select">MODEL</label>
            <div className="selectShell">
              <select id="model-select" value={modelId} onChange={(event) => setModelId(event.target.value)}>
                <optgroup label="V2 models · historical benchmark">
                  {v2Models.map((item) => (
                    <option key={item.id} value={item.id}>V2 · {item.label}</option>
                  ))}
                </optgroup>
                <optgroup label="V1 control">
                  {v1Models.map((item) => (
                    <option key={item.id} value={item.id}>V1 · {item.label}</option>
                  ))}
                </optgroup>
                <optgroup label="V3 research backlog · not frozen">
                  {futureModels.map((item) => <option key={item} disabled>V3 · {item} · not frozen</option>)}
                </optgroup>
              </select>
              <span className="selectChevron">⌄</span>
            </div>
          </div>

          <div className="modelSummary" key={`summary-${model.id}`}>
            <span className={model.id === "HGB_XS_MARKET" ? "modelBadge champion" : "modelBadge"}>{model.badge}</span>
            <div>
              <strong>{model.generation} · {model.label}</strong>
              <p>{model.description}</p>
            </div>
          </div>
        </section>

        <section className="metricStrip" key={`metrics-${model.id}`}>
          <article>
            <span>Median ΔPR-AUC</span>
            <strong className="primaryValue">+{pct(model.medianDeltaPr)}</strong>
            <small>vs fold prevalence</small>
          </article>
          <article>
            <span>Median ROC-AUC</span>
            <strong>{model.medianRoc.toFixed(4)}</strong>
            <small>ranking discrimination</small>
          </article>
          <article>
            <span>Median Q5 − Q1</span>
            <strong className="primaryValue">+{pct(model.medianQSpread)}</strong>
            <small>TP-rate spread</small>
          </article>
          <article>
            <span>Positive ΔPR folds</span>
            <strong>{model.positiveDeltaFolds}</strong>
            <small>chronological folds</small>
          </article>
        </section>

        <section className="mainGrid">
          <article className="surface chartPanel">
            <div className="sectionHead">
              <div>
                <span>HISTORICAL ROBUSTNESS</span>
                <h2>Chronological fold performance</h2>
              </div>
              <div className="legend"><i /> Δ PR-AUC</div>
            </div>
            <FoldChart model={model} />
            <div className="chartNote">
              <span>Hover each point for ROC-AUC and Q5−Q1.</span>
              <span className={model.folds[model.folds.length - 1].roc >= 0.5 ? "" : "warningText"}>
                Latest fold ROC {model.folds[model.folds.length - 1].roc.toFixed(3)}
              </span>
            </div>
          </article>

          <article className="surface forwardPanel">
            <div className="sectionHead compact">
              <div>
                <span>FORWARD VALIDATION</span>
                <h2>{championForward ? "V2 independent test" : "No forward contract"}</h2>
              </div>
              <span className={championForward ? "statusBadge amber" : "statusBadge"}>{championForward ? "LOCKED" : "HISTORICAL"}</span>
            </div>

            {championForward ? (
              <>
                <div className="forwardCount"><strong>0</strong><span>/ 100 sessions</span></div>
                <div className="progressTrack"><span style={{ width: "0%" }} /></div>
                <p className="forwardCopy">Signal sessions will be tracked independently from the sealed H10 outcomes. The V2 counter moves only after its model run finishes and the artifact is verified.</p>
                <div className="forwardFacts">
                  <div><span>Champion</span><strong><i className="okDot" /> V2 · HGB XS + Market</strong></div>
                  <div><span>Model artifact</span><strong><i className="okDot" /> Frozen & verified</strong></div>
                  <div><span>Outcome access</span><strong>Locked</strong></div>
                </div>
                <a className="primaryLink" href="/monitoring">Open Forward Monitoring →</a>
              </>
            ) : (
              <div className="noForward">
                <div className="noForwardIcon">↗</div>
                <h3>Historical evidence only</h3>
                <p>This candidate was not selected for the frozen V2 forward test. Switch to V2 · HGB XS + Market to inspect the active contract.</p>
              </div>
            )}
          </article>
        </section>

        <section className="surface comparisonPanel" id="models">
          <div className="sectionHead">
            <div>
              <span>MODEL COMPARISON</span>
              <h2>Historical benchmark</h2>
            </div>
            <span className="tableHint">Click a row to inspect</span>
          </div>
          <div className="tableScroll">
            <table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Model</th>
                  <th>ΔPR-AUC</th>
                  <th>ROC-AUC</th>
                  <th>Q5−Q1</th>
                  <th>Folds</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map((item) => (
                  <tr key={item.id} className={item.id === model.id ? "selectedRow" : ""} onClick={() => setModelId(item.id)}>
                    <td><span className={`generationPill ${item.generation.toLowerCase()}`}>{item.generation}</span></td>
                    <td><strong>{item.label}</strong><small>{item.id}</small></td>
                    <td className="primaryCell">+{pct(item.medianDeltaPr)}</td>
                    <td>{item.medianRoc.toFixed(4)}</td>
                    <td className="primaryCell">+{pct(item.medianQSpread)}</td>
                    <td>{item.positiveDeltaFolds}</td>
                    <td>{item.id === "HGB_XS_MARKET" ? <span className="championLabel">Champion</span> : item.id === "V1_HGB_CONTROL" ? "Control" : "Candidate"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="pageFooter">
          <span>IDX Trade · exploratory research only</span>
          <span>Reserved forward outcomes are not rendered.</span>
        </div>
      </div>
    </main>
  );
}
