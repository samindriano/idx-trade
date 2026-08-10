"use client";

import { useMemo, useState } from "react";

type ModelMonitor = {
  generation: string;
  modelId: string;
  name: string;
  frozen: boolean;
  state: "WAITING_FOR_DATA" | "QUEUED" | "PREPARING" | "SCORING" | "WRITING" | "DONE" | "FAILED" | "NOT_FROZEN";
  progress: number;
  completedSessions: number;
  targetSessions: number | null;
  artifactVerified: boolean;
};

const monitorModels: ModelMonitor[] = [
  {
    generation: "V2",
    modelId: "HGB_XS_MARKET",
    name: "HGB XS + Market",
    frozen: true,
    state: "WAITING_FOR_DATA",
    progress: 0,
    completedSessions: 0,
    targetSessions: 100,
    artifactVerified: true,
  },
  {
    generation: "V3",
    modelId: "FUTURE_V3_CHAMPION",
    name: "Future champion",
    frozen: false,
    state: "NOT_FROZEN",
    progress: 0,
    completedSessions: 0,
    targetSessions: null,
    artifactVerified: false,
  },
  {
    generation: "V4",
    modelId: "FUTURE_V4_CHAMPION",
    name: "Future champion",
    frozen: false,
    state: "NOT_FROZEN",
    progress: 0,
    completedSessions: 0,
    targetSessions: null,
    artifactVerified: false,
  },
];

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

function stateLabel(state: ModelMonitor["state"]) {
  switch (state) {
    case "WAITING_FOR_DATA": return "Waiting for data";
    case "QUEUED": return "Queued";
    case "PREPARING": return "Preparing";
    case "SCORING": return "Scoring";
    case "WRITING": return "Writing artifact";
    case "DONE": return "Done";
    case "FAILED": return "Failed";
    case "NOT_FROZEN": return "Not frozen";
  }
}

export default function MonitoringPage() {
  const [targetDate, setTargetDate] = useState("");
  const runtimeConnected = false;
  const dataReadySessions = 0;
  const nextMissingSession: string | null = null;

  const v2 = monitorModels[0];
  const monitorable = useMemo(() => monitorModels.filter((item) => item.frozen), []);

  return (
    <main className="appShell monitorShell">
      <header className="topNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home">
            <Logo />
            <span>IDX Trade</span>
          </a>
          <nav className="primaryNav" aria-label="Primary navigation">
            <a href="/#overview">Overview</a>
            <a href="/#models">Models</a>
            <a className="active" href="/monitoring">Forward Monitoring</a>
          </nav>
          <div className="researchPill"><span className="liveDot" /> Research only</div>
        </div>
      </header>

      <div className="page monitoringPage">
        <section className="monitorHero">
          <div>
            <p className="eyebrow">FORWARD MONITORING</p>
            <h1>Capture once. Run models independently.</h1>
            <p>One button owns the market-data snapshot for a session. After the snapshot is frozen, every eligible champion model can run in parallel without sharing one global progress state.</p>
          </div>
          <div className="monitorHeroBadges">
            <span className="lockBadge"><span className="lockDot" /> Outcomes locked</span>
            <span className="runtimeBadge offline"><i /> Runtime adapter pending</span>
          </div>
        </section>

        <section className="monitorSummaryGrid">
          <article className="summaryBlock prominent">
            <span>V2 forward progress</span>
            <div><strong>{v2.completedSessions}</strong><em>/ {v2.targetSessions} sessions</em></div>
            <small>Counts only verified V2 model artifacts — never data-fetch attempts.</small>
          </article>
          <article className="summaryBlock">
            <span>Data snapshots ready</span>
            <strong>{dataReadySessions}</strong>
            <small>Canonical session snapshots</small>
          </article>
          <article className="summaryBlock">
            <span>Next missing session</span>
            <strong className="summaryTextValue">{nextMissingSession ?? "Not synced"}</strong>
            <small>Earliest missing eligible IDX session</small>
          </article>
          <article className="summaryBlock">
            <span>Outcome access</span>
            <strong className="summaryTextValue">LOCKED</strong>
            <small>H10 verdict remains sealed</small>
          </article>
        </section>

        <section className="monitorMainGrid">
          <article className="surface sessionCapturePanel">
            <div className="sectionHead">
              <div>
                <span>SESSION DATA</span>
                <h2>Capture an exact IDX session</h2>
              </div>
              <span className="statusBadge indigo">SESSION-FIRST</span>
            </div>

            <div className="captureBody">
              <p className="captureLead">If several sessions were missed, the default target will be the earliest missing closed IDX session. Already verified dates are skipped automatically after restart.</p>

              <div className="captureControls">
                <label>
                  <span>Target session</span>
                  <input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
                </label>
                <button className="captureButton" type="button" disabled={!runtimeConnected || !targetDate}>
                  Ambil Data {targetDate ? new Date(`${targetDate}T00:00:00`).toLocaleDateString("id-ID", { day: "numeric", month: "short" }) : "Session"}
                </button>
              </div>

              {!runtimeConnected && (
                <div className="runtimeNotice">
                  <i />
                  <div>
                    <strong>Frontend contract ready; local runtime is not wired yet.</strong>
                    <p>The button stays disabled rather than pretending a fetch succeeded. The local adapter will bind this exact-date action to the persistent session registry and Python data pipeline.</p>
                  </div>
                </div>
              )}

              <div className="sessionStripHeader">
                <div>
                  <span>SESSION HISTORY</span>
                  <h3>Recorded, missing, and future dates</h3>
                </div>
                <div className="sessionLegend">
                  <span><i className="legendDone" /> Recorded</span>
                  <span><i className="legendMissing" /> Missing</span>
                  <span><i className="legendFuture" /> Future</span>
                </div>
              </div>

              <div className="emptySessionState">
                <div className="emptySessionIcon">↳</div>
                <strong>No canonical session registry connected yet</strong>
                <p>When the local coordinator is wired, this strip is rebuilt from durable state after every refresh. Completed dates will never reset to zero or be offered for download again.</p>
              </div>
            </div>
          </article>

          <article className="surface v2ContractPanel">
            <div className="sectionHead compact">
              <div>
                <span>ACTIVE CONTRACT</span>
                <h2>V2 · HGB XS + Market</h2>
              </div>
              <span className="modelBadge champion">V2 CHAMPION</span>
            </div>
            <div className="contractProgress">
              <div className="contractNumber"><strong>{v2.completedSessions}</strong><span>/ {v2.targetSessions}</span></div>
              <div className="progressTrack indigoTrack"><span style={{ width: `${(v2.completedSessions / (v2.targetSessions ?? 100)) * 100}%` }} /></div>
            </div>
            <div className="contractFacts">
              <div><span>Final model</span><strong><i className="okDot" /> Frozen</strong></div>
              <div><span>Artifact</span><strong><i className="okDot" /> Verified</strong></div>
              <div><span>Session complete when</span><strong>Model artifact DONE</strong></div>
              <div><span>Outcome access</span><strong>Locked</strong></div>
            </div>
            <p className="contractNote">A DATA_READY session does not increment this counter. V2 advances only after HGB_XS_MARKET finishes scoring and its immutable output passes verification.</p>
          </article>
        </section>

        <section className="surface modelRunsPanel">
          <div className="sectionHead">
            <div>
              <span>CHAMPION RUNS</span>
              <h2>Independent model progress</h2>
            </div>
            <span className="tableHint">No global progress bar</span>
          </div>

          <div className="modelRunList">
            {monitorModels.map((item) => (
              <article className={`modelRunRow ${item.frozen ? "" : "futureRun"}`} key={item.modelId}>
                <div className="runIdentity">
                  <span className={`generationPill ${item.generation.toLowerCase()}`}>{item.generation}</span>
                  <div>
                    <strong>{item.name}</strong>
                    <small>{item.frozen ? item.modelId : "Appears automatically after this generation has a frozen champion"}</small>
                  </div>
                </div>

                <div className="runProgressBlock">
                  <div className="runProgressHead">
                    <span>{stateLabel(item.state)}</span>
                    {item.frozen && <em>{Math.round(item.progress * 100)}%</em>}
                  </div>
                  <div className={`runTrack ${item.state === "FAILED" ? "failed" : ""}`}>
                    <span style={{ width: `${item.progress * 100}%` }} />
                  </div>
                </div>

                <div className="runMeta">
                  {item.frozen ? (
                    <>
                      <span>{item.completedSessions}/{item.targetSessions ?? "—"} sessions</span>
                      <strong>{item.artifactVerified ? "Model verified" : "Awaiting verification"}</strong>
                    </>
                  ) : (
                    <>
                      <span>Research generation</span>
                      <strong>Not monitorable yet</strong>
                    </>
                  )}
                </div>
              </article>
            ))}
          </div>

          <div className="parallelRule">
            <strong>{monitorable.length} frozen champion currently monitorable.</strong>
            <span>When V3/V4 champions are frozen, each date gets a separate run state per model. One model may be DONE while another is still SCORING or FAILED; successful models are never rolled back.</span>
          </div>
        </section>

        <section className="recoveryBand">
          <div>
            <span>CRASH / RESTART RECOVERY</span>
            <h2>Resume from verified state, not from the old progress bar.</h2>
          </div>
          <div className="recoverySteps">
            <span><b>1</b> Skip DATA_READY dates</span>
            <span><b>2</b> Skip verified DONE model runs</span>
            <span><b>3</b> Requeue only interrupted gaps</span>
          </div>
        </section>

        <div className="pageFooter">
          <span>IDX Trade · forward signal monitoring</span>
          <span>Reserved H10 outcomes remain inaccessible.</span>
        </div>
      </div>
    </main>
  );
}
