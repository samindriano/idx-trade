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
  label: string;
  badge: string;
  status: string;
  description: string;
  medianDeltaPr: number;
  medianRoc: number;
  medianQSpread: number;
  positiveDeltaFolds: string;
  positiveQFolds: string;
  rocPositiveFolds: string;
  folds: FoldMetric[];
};

const models: Record<string, ModelRecord> = {
  HGB_XS_MARKET: {
    id: "HGB_XS_MARKET",
    label: "HGB XS + Market",
    badge: "V2 CHAMPION",
    status: "Frozen · historical-development",
    description: "Cross-sectional stock ranks + explicit market state + stock-relative-to-market features.",
    medianDeltaPr: 0.02388,
    medianRoc: 0.52441,
    medianQSpread: 0.051196,
    positiveDeltaFolds: "6 / 6",
    positiveQFolds: "6 / 6",
    rocPositiveFolds: "5 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.021677, roc: 0.525558, qSpread: 0.084017 },
      { fold: "F2", deltaPr: 0.028999, roc: 0.523262, qSpread: 0.070311 },
      { fold: "F3", deltaPr: 0.008789, roc: 0.527379, qSpread: 0.038651 },
      { fold: "F4", deltaPr: 0.038295, roc: 0.512827, qSpread: 0.057535 },
      { fold: "F5", deltaPr: 0.026082, roc: 0.530579, qSpread: 0.032179 },
      { fold: "F6", deltaPr: 0.018643, roc: 0.493102, qSpread: 0.044856 },
    ],
  },
  HGB_XS: {
    id: "HGB_XS",
    label: "HGB XS",
    badge: "V2",
    status: "Historical candidate",
    description: "Nonlinear HGB on same-date cross-sectional stock features without explicit market context.",
    medianDeltaPr: 0.018482,
    medianRoc: 0.515711,
    medianQSpread: 0.036905,
    positiveDeltaFolds: "6 / 6",
    positiveQFolds: "6 / 6",
    rocPositiveFolds: "6 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.020569, roc: 0.513621, qSpread: 0.03434 },
      { fold: "F2", deltaPr: 0.03865, roc: 0.533146, qSpread: 0.08415 },
      { fold: "F3", deltaPr: 0.023723, roc: 0.516927, qSpread: 0.048323 },
      { fold: "F4", deltaPr: 0.015208, roc: 0.516375, qSpread: 0.037645 },
      { fold: "F5", deltaPr: 0.013105, roc: 0.513975, qSpread: 0.036164 },
      { fold: "F6", deltaPr: 0.016394, roc: 0.515047, qSpread: 0.018103 },
    ],
  },
  LOGISTIC_XS: {
    id: "LOGISTIC_XS",
    label: "Logistic XS",
    badge: "V2",
    status: "Historical candidate",
    description: "Linear cross-sectional baseline for testing whether normalization alone improves transportability.",
    medianDeltaPr: 0.009372,
    medianRoc: 0.506269,
    medianQSpread: 0.019726,
    positiveDeltaFolds: "6 / 6",
    positiveQFolds: "5 / 6",
    rocPositiveFolds: "5 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.009908, roc: 0.502548, qSpread: 0.029134 },
      { fold: "F2", deltaPr: 0.030582, roc: 0.528439, qSpread: 0.07807 },
      { fold: "F3", deltaPr: 0.010496, roc: 0.511545, qSpread: 0.026872 },
      { fold: "F4", deltaPr: 0.003873, roc: 0.495587, qSpread: -0.000081 },
      { fold: "F5", deltaPr: 0.008835, roc: 0.507063, qSpread: 0.012579 },
      { fold: "F6", deltaPr: 0.003217, roc: 0.505476, qSpread: 0.005455 },
    ],
  },
  PAIRWISE_XS: {
    id: "PAIRWISE_XS",
    label: "Pairwise Logistic XS",
    badge: "V2",
    status: "Historical candidate",
    description: "Linear same-date pairwise ranking experiment; useful as an objective-function diagnostic.",
    medianDeltaPr: 0.01067,
    medianRoc: 0.508343,
    medianQSpread: 0.024926,
    positiveDeltaFolds: "6 / 6",
    positiveQFolds: "6 / 6",
    rocPositiveFolds: "6 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.010404, roc: 0.501659, qSpread: 0.018493 },
      { fold: "F2", deltaPr: 0.027711, roc: 0.525379, qSpread: 0.067298 },
      { fold: "F3", deltaPr: 0.010936, roc: 0.511762, qSpread: 0.031359 },
      { fold: "F4", deltaPr: 0.008887, roc: 0.501757, qSpread: 0.012202 },
      { fold: "F5", deltaPr: 0.015098, roc: 0.516769, qSpread: 0.040615 },
      { fold: "F6", deltaPr: 0.002926, roc: 0.504925, qSpread: 0.003426 },
    ],
  },
  V1_HGB_CONTROL: {
    id: "V1_HGB_CONTROL",
    label: "V1 HGB Control",
    badge: "CONTROL",
    status: "Historical control · not champion-eligible",
    description: "Original HGB feature set retained only as the locked V2 comparison control.",
    medianDeltaPr: 0.022348,
    medianRoc: 0.51901,
    medianQSpread: 0.031008,
    positiveDeltaFolds: "6 / 6",
    positiveQFolds: "6 / 6",
    rocPositiveFolds: "5 / 6",
    folds: [
      { fold: "F1", deltaPr: 0.017436, roc: 0.512096, qSpread: 0.020781 },
      { fold: "F2", deltaPr: 0.03315, roc: 0.528622, qSpread: 0.068228 },
      { fold: "F3", deltaPr: 0.000785, roc: 0.485803, qSpread: 0.005463 },
      { fold: "F4", deltaPr: 0.028493, roc: 0.533356, qSpread: 0.023201 },
      { fold: "F5", deltaPr: 0.016653, roc: 0.509485, qSpread: 0.038815 },
      { fold: "F6", deltaPr: 0.02726, roc: 0.525924, qSpread: 0.044931 },
    ],
  },
};

const futureModels = ["V3-RECENCY", "V3-REGIME", "V3-SECTOR", "V3-TRUE-RANKING"];

function pct(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`;
}

function metricWidth(value: number, max: number) {
  return `${Math.min(100, Math.max(1.5, (Math.abs(value) / max) * 100))}%`;
}

function LogoMark() {
  return (
    <div className="logoMark" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}

function StatusDot({ tone = "green" }: { tone?: "green" | "amber" | "muted" }) {
  return <span className={`statusDot ${tone}`} />;
}

export default function Home() {
  const [modelId, setModelId] = useState("HGB_XS_MARKET");
  const [view, setView] = useState<"historical" | "forward">("historical");
  const model = models[modelId];

  const bestFold = useMemo(
    () => model.folds.reduce((best, fold) => (fold.deltaPr > best.deltaPr ? fold : best), model.folds[0]),
    [model]
  );

  const weakestFold = useMemo(
    () => model.folds.reduce((worst, fold) => (fold.deltaPr < worst.deltaPr ? fold : worst), model.folds[0]),
    [model]
  );

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <LogoMark />
          <div>
            <strong>IDX TRADE</strong>
            <span>RESEARCH TERMINAL</span>
          </div>
        </div>

        <nav className="nav">
          <a className="active" href="#overview"><span>01</span>Overview</a>
          <a href="#forward"><span>02</span>Forward monitor</a>
          <a href="#folds"><span>03</span>Fold diagnostics</a>
          <a href="#models"><span>04</span>Model registry</a>
          <a href="#research"><span>05</span>Research lane</a>
        </nav>

        <div className="sidebarBottom">
          <div className="environment">
            <span>ENVIRONMENT</span>
            <strong><StatusDot /> Research only</strong>
          </div>
          <div className="tinyMeta">
            <span>Branch</span>
            <code>frontend/model-monitoring-v1</code>
          </div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <div className="eyebrow">MODEL OBSERVATORY / IDX</div>
            <h1>Forward Research Monitor</h1>
          </div>
          <div className="topbarRight">
            <div className="guardrail"><StatusDot tone="amber" />Forward outcomes locked</div>
            <div className="avatar">ST</div>
          </div>
        </header>

        <div className="content" id="overview">
          <section className="controlStrip">
            <div className="controlBlock modelControl">
              <label htmlFor="model">ACTIVE MODEL</label>
              <div className="selectWrap">
                <select id="model" value={modelId} onChange={(event) => setModelId(event.target.value)}>
                  <optgroup label="Historical models">
                    {Object.values(models).map((item) => (
                      <option key={item.id} value={item.id}>{item.label}</option>
                    ))}
                  </optgroup>
                  <optgroup label="V3 research backlog">
                    {futureModels.map((item) => <option key={item} disabled>{item} · not frozen</option>)}
                  </optgroup>
                </select>
                <span className="chevron">⌄</span>
              </div>
            </div>

            <div className="controlBlock">
              <label>VIEW</label>
              <div className="segmented">
                <button className={view === "historical" ? "selected" : ""} onClick={() => setView("historical")}>Historical</button>
                <button className={view === "forward" ? "selected" : ""} onClick={() => setView("forward")}>Forward</button>
              </div>
            </div>

            <div className="modelIdentity">
              <span className="tag">{model.badge}</span>
              <div>
                <strong>{model.id}</strong>
                <span>{model.status}</span>
              </div>
            </div>
          </section>

          <div className="notice">
            <span className="noticeIcon">!</span>
            <p><strong>No fresh-forward outcome data is rendered.</strong> This UI contains frozen historical benchmark evidence and readiness metadata only. Forward results remain unavailable until the separate one-shot authorization gate.</p>
          </div>

          {view === "historical" ? (
            <>
              <section className="metricGrid">
                <article className="metricCard featured">
                  <span>MEDIAN Δ PR-AUC</span>
                  <strong>{pct(model.medianDeltaPr)}</strong>
                  <small>vs fold prevalence</small>
                </article>
                <article className="metricCard">
                  <span>MEDIAN ROC-AUC</span>
                  <strong>{model.medianRoc.toFixed(4)}</strong>
                  <small>{model.rocPositiveFolds} folds above 0.50</small>
                </article>
                <article className="metricCard">
                  <span>MEDIAN Q5 − Q1</span>
                  <strong>{pct(model.medianQSpread)}</strong>
                  <small>TP-rate spread</small>
                </article>
                <article className="metricCard">
                  <span>POSITIVE ΔPR FOLDS</span>
                  <strong>{model.positiveDeltaFolds}</strong>
                  <small>chronological validation</small>
                </article>
              </section>

              <section className="dashboardGrid">
                <article className="panel performancePanel" id="folds">
                  <div className="panelHeader">
                    <div>
                      <span className="sectionLabel">ROBUSTNESS</span>
                      <h2>Chronological fold profile</h2>
                    </div>
                    <div className="legend"><span className="legendBar" />Δ PR-AUC</div>
                  </div>

                  <div className="foldChart">
                    {model.folds.map((fold) => (
                      <div className="foldRow" key={fold.fold}>
                        <span className="foldLabel">{fold.fold}</span>
                        <div className="barTrack">
                          <div className="barFill" style={{ width: metricWidth(fold.deltaPr, 0.04) }} />
                        </div>
                        <strong>{pct(fold.deltaPr)}</strong>
                        <span className={fold.roc >= 0.5 ? "roc positive" : "roc negative"}>ROC {fold.roc.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="chartFooter">
                    <div><span>Best fold</span><strong>{bestFold.fold} · {pct(bestFold.deltaPr)}</strong></div>
                    <div><span>Weakest fold</span><strong>{weakestFold.fold} · {pct(weakestFold.deltaPr)}</strong></div>
                    <div><span>Q5−Q1 positive</span><strong>{model.positiveQFolds}</strong></div>
                  </div>
                </article>

                <article className="panel thesisPanel">
                  <div className="panelHeader">
                    <div>
                      <span className="sectionLabel">MODEL THESIS</span>
                      <h2>What this model reads</h2>
                    </div>
                  </div>
                  <p>{model.description}</p>
                  <div className="featureStack">
                    <div><span className="featureNum">10</span><span><strong>Cross-sectional stock ranks</strong><small>momentum · ATR · volume · range position · liquidity</small></span></div>
                    <div><span className="featureNum">09</span><span><strong>Market-state features</strong><small>breadth · median returns · volatility · active universe</small></span></div>
                    <div><span className="featureNum">06</span><span><strong>Stock-vs-market features</strong><small>relative momentum · volatility · range · volume · value</small></span></div>
                  </div>
                  {model.id !== "HGB_XS_MARKET" && <div className="contextNote">Feature stack shown is the V2 champion architecture. Selected candidate differs; use fold metrics above for candidate comparison.</div>}
                </article>
              </section>
            </>
          ) : (
            <section className="forwardLayout" id="forward">
              <article className="panel forwardHero">
                <div className="lockGlyph">◫</div>
                <span className="sectionLabel">ONE-SHOT FORWARD VALIDATION</span>
                <h2>Outcome access is intentionally locked.</h2>
                <p>The final V2 champion is frozen and the outcome-blind runtime exists. The dashboard will only populate forward outcome metrics after a complete immutable 100-session H10-mature block receives separate authorization.</p>
                <div className="progressMeta"><span>OUTCOMES CONSUMED</span><strong>0 / 100</strong></div>
                <div className="progressTrack"><span style={{ width: "0%" }} /></div>
                <div className="readinessGrid">
                  <div><span>Final model</span><strong><StatusDot /> Frozen</strong></div>
                  <div><span>Artifact verification</span><strong><StatusDot /> Valid</strong></div>
                  <div><span>100-session readiness</span><strong><StatusDot tone="muted" /> Not evaluated</strong></div>
                  <div><span>Outcome marker</span><strong><StatusDot tone="muted" /> Absent</strong></div>
                </div>
              </article>

              <article className="panel sessionPanel">
                <div className="panelHeader">
                  <div>
                    <span className="sectionLabel">SESSION LEDGER</span>
                    <h2>Forward sessions</h2>
                  </div>
                  <span className="tag subtle">OUTCOME-BLIND</span>
                </div>
                <div className="emptyTable">
                  <div className="tableHead"><span>Session</span><span>Universe</span><span>Rank output</span><span>H10 maturity</span><span>Outcome</span></div>
                  <div className="emptyState">
                    <span>∅</span>
                    <strong>No authorized forward outcome rows</strong>
                    <p>Future data adapter can populate signal-side monitoring without exposing labels; outcome columns stay sealed until the gate opens.</p>
                  </div>
                </div>
              </article>
            </section>
          )}

          <section className="lowerGrid" id="models">
            <article className="panel registryPanel">
              <div className="panelHeader">
                <div>
                  <span className="sectionLabel">MODEL REGISTRY</span>
                  <h2>Frozen artifacts</h2>
                </div>
              </div>
              <div className="registryRows">
                <div><span>Champion</span><strong>HGB_XS_MARKET</strong></div>
                <div><span>Training rows</span><strong>292,633</strong></div>
                <div><span>Tickers</span><strong>737</strong></div>
                <div><span>Sessions</span><strong>20..1250</strong></div>
                <div><span>Model SHA-256</span><code>5c9e3d02…15cb9ace</code></div>
                <div><span>Manifest SHA-256</span><code>f4834500…7c3ace9</code></div>
              </div>
            </article>

            <article className="panel researchPanel" id="research">
              <div className="panelHeader">
                <div>
                  <span className="sectionLabel">PARALLEL RESEARCH</span>
                  <h2>V3 experiment lane</h2>
                </div>
                <span className="tag subtle">BACKLOG</span>
              </div>
              <div className="researchList">
                <div><span className="researchIndex">A</span><span><strong>Recency weighting</strong><small>Test training-age / non-stationarity.</small></span><em>FIRST</em></div>
                <div><span className="researchIndex">B</span><span><strong>Regime-aware experts</strong><small>Separate mappings across causal market states.</small></span><em>QUEUED</em></div>
                <div><span className="researchIndex">C</span><span><strong>PIT sector relative</strong><small>Stock vs sector + sector vs market.</small></span><em>DATA GATE</em></div>
                <div><span className="researchIndex">D</span><span><strong>True learning-to-rank</strong><small>Nonlinear same-date ranking objective.</small></span><em>QUEUED</em></div>
              </div>
            </article>
          </section>

          <footer>
            <span>IDX Trade · exploratory research only</span>
            <span>Historical benchmark snapshot · 2026-08-10</span>
          </footer>
        </div>
      </section>
    </main>
  );
}
