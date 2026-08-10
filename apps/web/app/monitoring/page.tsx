"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type SessionState = "AVAILABLE" | "FETCHING" | "DATA_READY" | "DATA_FAILED";

type MonitorSession = {
  session_date: string;
  state: SessionState;
  error_code: string | null;
  error_message: string | null;
  completed_at: string | null;
};

type RuntimeModelRun = {
  session_date: string;
  model_id: string;
  model_fingerprint: string;
  generation: string;
  state: string;
  progress_fraction: number;
  artifact_sha256?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
};

type MonitorRuntimeStatus = {
  runtime_ready: boolean;
  calendar_ready: boolean;
  calendar_first_session: string | null;
  calendar_last_session: string | null;
  next_missing_session: string | null;
  data_ready_sessions: number;
  sessions: MonitorSession[];
  model_runs: RuntimeModelRun[];
  outcome_access: "LOCKED";
};

type StatusResponse = {
  connected: boolean;
  configured: boolean;
  status?: MonitorRuntimeStatus;
  error?: string;
  detail?: string | null;
};

type GenerationSlot = {
  generation: "V2" | "V3" | "V4";
  modelId: string;
  name: string;
  frozen: boolean;
  targetSessions: number | null;
};

const generationSlots: GenerationSlot[] = [
  {
    generation: "V2",
    modelId: "HGB_XS_MARKET",
    name: "HGB XS + Market",
    frozen: true,
    targetSessions: 100,
  },
  {
    generation: "V3",
    modelId: "FUTURE_V3_CHAMPION",
    name: "Future champion",
    frozen: false,
    targetSessions: null,
  },
  {
    generation: "V4",
    modelId: "FUTURE_V4_CHAMPION",
    name: "Future champion",
    frozen: false,
    targetSessions: null,
  },
];

function Logo() {
  return (
    <div className="brandMark" aria-hidden="true">
      <span /><span /><span /><span />
    </div>
  );
}

function shortDate(value: string | null) {
  if (!value) return "Not synced";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function buttonDate(value: string | null) {
  if (!value) return "Next Session";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function sessionLabel(state: SessionState) {
  if (state === "DATA_READY") return "Recorded";
  if (state === "FETCHING") return "Fetching";
  if (state === "DATA_FAILED") return "Failed";
  return "Missing";
}

export default function MonitoringPage() {
  const [status, setStatus] = useState<MonitorRuntimeStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [requestDetail, setRequestDetail] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [targetDate, setTargetDate] = useState("");

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/monitor/status", { cache: "no-store" });
      const payload = (await response.json()) as StatusResponse;
      setConnected(Boolean(payload.connected));
      setConfigured(Boolean(payload.configured));
      if (payload.status) {
        setStatus(payload.status);
        setRequestError(null);
        setRequestDetail(null);
        setTargetDate((current) => current || payload.status?.next_missing_session || "");
      } else {
        setRequestError(payload.error ?? "Local monitoring runtime is unavailable.");
        setRequestDetail(payload.detail ?? null);
      }
    } catch (error) {
      setConnected(false);
      setRequestError(error instanceof Error ? error.message : "Monitoring status cannot be read.");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!status?.next_missing_session) return;
    const selected = status.sessions.find((item) => item.session_date === targetDate);
    if (!targetDate || selected?.state === "DATA_READY") {
      setTargetDate(status.next_missing_session);
    }
  }, [status, targetDate]);

  async function capture() {
    setSubmitting(true);
    setRequestError(null);
    setRequestDetail(null);
    try {
      const response = await fetch("/api/monitor/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: targetDate || null }),
      });
      const payload = (await response.json()) as {
        accepted?: boolean;
        target_session?: string | null;
        reason?: string;
        error?: string;
        detail?: string | null;
      };
      if (!response.ok) {
        throw new Error(payload.detail ? `${payload.error ?? "Capture failed"} — ${payload.detail}` : payload.error ?? "Capture failed");
      }
      if (payload.reason === "NO_MISSING_SESSION") {
        setRequestError("All currently known closed IDX sessions are already recorded.");
      }
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      await refresh();
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Session capture could not be started.");
    } finally {
      setSubmitting(false);
    }
  }

  const v2DoneDates = useMemo(() => {
    if (!status) return new Set<string>();
    return new Set(
      status.model_runs
        .filter((run) => run.model_id === "HGB_XS_MARKET" && run.state === "DONE" && Boolean(run.artifact_sha256))
        .map((run) => run.session_date),
    );
  }, [status]);

  const latestRuns = useMemo(() => {
    const map = new Map<string, RuntimeModelRun>();
    for (const run of status?.model_runs ?? []) {
      const existing = map.get(run.model_id);
      if (!existing || run.session_date >= existing.session_date) map.set(run.model_id, run);
    }
    return map;
  }, [status]);

  const latestFailure = [...(status?.sessions ?? [])]
    .reverse()
    .find((session) => session.state === "DATA_FAILED");
  const anyFetching = status?.sessions.some((session) => session.state === "FETCHING") ?? false;
  const calendarReady = status?.calendar_ready ?? false;
  const captureTarget = targetDate || status?.next_missing_session || null;
  const canCapture = configured && connected && !submitting && !anyFetching;

  return (
    <main className="appShell monitorShell">
      <header className="topNav">
        <div className="navInner">
          <a className="brand" href="/" aria-label="IDX Trade home"><Logo /><span>IDX Trade</span></a>
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
            <p>Ambil satu snapshot EOD yang immutable. Session yang sudah terekam tidak diambil ulang; model champion memakai snapshot yang sama dan punya progress sendiri.</p>
          </div>
          <div className="monitorHeroBadges">
            <span className="lockBadge"><span className="lockDot" /> Outcomes locked</span>
            <span className={`runtimeBadge ${connected ? "online" : "offline"}`}><i /> {connected ? "Runtime connected" : "Runtime offline"}</span>
          </div>
        </section>

        <section className="monitorSummaryGrid">
          <article className="summaryBlock prominent">
            <span>V2 forward progress</span>
            <div><strong>{v2DoneDates.size}</strong><em>/ 100 sessions</em></div>
            <small>Naik hanya setelah output V2 DONE + artifact verified.</small>
          </article>
          <article className="summaryBlock">
            <span>Data snapshots ready</span>
            <strong>{status?.data_ready_sessions ?? 0}</strong>
            <small>Canonical session snapshots</small>
          </article>
          <article className="summaryBlock">
            <span>Next missing session</span>
            <strong className="summaryTextValue">{shortDate(status?.next_missing_session ?? null)}</strong>
            <small>Earliest missing eligible IDX session</small>
          </article>
          <article className="summaryBlock">
            <span>Outcome access</span>
            <strong className="summaryTextValue">LOCKED</strong>
            <small>H10 verdict tetap tidak dibaca</small>
          </article>
        </section>

        <section className="monitorMainGrid">
          <article className="surface sessionCapturePanel">
            <div className="sectionHead">
              <div><span>SESSION DATA</span><h2>Ambil data satu tanggal</h2></div>
              <span className="statusBadge indigo">SESSION-FIRST</span>
            </div>

            <div className="captureBody">
              <p className="captureLead">Default selalu tanggal bursa paling awal yang belum terekam. Kalau app mati, registry dibaca ulang dan session DATA_READY otomatis di-skip.</p>

              <div className="captureControls">
                <label>
                  <span>Target session</span>
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(event) => setTargetDate(event.target.value)}
                    min={status?.calendar_first_session ?? undefined}
                    max={status?.calendar_last_session ?? undefined}
                  />
                </label>
                <button className="captureButton" type="button" disabled={!canCapture} onClick={() => void capture()}>
                  {submitting ? "Menyiapkan..." : anyFetching ? "Sedang mengambil data..." : `Ambil Data ${buttonDate(captureTarget)}`}
                </button>
              </div>

              {!configured && (
                <div className="runtimeNotice"><i /><div><strong>Runtime path belum dikonfigurasi.</strong><p>Set sekali `IDX_TRADE_RUNTIME_ROOT` dan `IDX_TRADE_PYTHON` di `.env.local`; setelah itu operasi harian tetap satu tombol.</p></div></div>
              )}
              {configured && !calendarReady && connected && (
                <div className="runtimeNotice info"><i /><div><strong>Forward calendar belum disinkronkan.</strong><p>Tombol pertama akan sinkronkan kalender resmi IDX lalu otomatis memilih session tertua yang belum terekam.</p></div></div>
              )}
              {requestError && (
                <div className="runtimeNotice danger"><i /><div><strong>{requestError}</strong>{requestDetail && <p>{requestDetail}</p>}</div></div>
              )}
              {latestFailure && !requestError && (
                <div className="runtimeNotice danger"><i /><div><strong>Capture {shortDate(latestFailure.session_date)} belum berhasil.</strong><p>{latestFailure.error_message ?? latestFailure.error_code ?? "Safe to retry after the blocker is fixed."}</p></div></div>
              )}

              <div className="sessionStripHeader">
                <div><span>SESSION HISTORY</span><h3>Recorded, missing, dan proses aktif</h3></div>
                <div className="sessionLegend">
                  <span><i className="legendDone" /> Recorded</span>
                  <span><i className="legendMissing" /> Missing</span>
                  <span><i className="legendFuture" /> Fetching</span>
                </div>
              </div>

              {status?.sessions.length ? (
                <div className="sessionStrip">
                  {status.sessions.slice(-12).map((session) => (
                    <button
                      type="button"
                      key={session.session_date}
                      className={`sessionTile ${session.state.toLowerCase()}`}
                      onClick={() => session.state !== "DATA_READY" && setTargetDate(session.session_date)}
                      title={session.error_message ?? undefined}
                    >
                      <span>{buttonDate(session.session_date)}</span>
                      <strong>{sessionLabel(session.state)}</strong>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="emptySessionState">
                  <div className="emptySessionIcon">↳</div>
                  <strong>{connected ? "Forward calendar belum punya snapshot" : "Belum terhubung ke canonical registry"}</strong>
                  <p>{connected ? "Klik Ambil Data sekali; calendar resmi disinkronkan dan earliest missing session dipilih otomatis." : "Begitu runtime tersambung, state durable akan direkonstruksi tanpa reset progress."}</p>
                </div>
              )}
            </div>
          </article>

          <article className="surface v2ContractPanel">
            <div className="sectionHead compact">
              <div><span>ACTIVE CONTRACT</span><h2>V2 · HGB XS + Market</h2></div>
              <span className="modelBadge champion">V2 CHAMPION</span>
            </div>
            <div className="contractProgress">
              <div className="contractNumber"><strong>{v2DoneDates.size}</strong><span>/ 100</span></div>
              <div className="progressTrack indigoTrack"><span style={{ width: `${v2DoneDates.size}%` }} /></div>
            </div>
            <div className="contractFacts">
              <div><span>Final model</span><strong><i className="okDot" /> Frozen</strong></div>
              <div><span>Model SHA</span><strong>5c9e3d02…</strong></div>
              <div><span>Session complete when</span><strong>Model artifact DONE</strong></div>
              <div><span>Outcome access</span><strong>Locked</strong></div>
            </div>
            <p className="contractNote">DATA_READY belum menambah 100-session counter. Counter hanya menghitung unique V2 result yang persisted dan verified.</p>
          </article>
        </section>

        <section className="surface modelRunsPanel">
          <div className="sectionHead">
            <div><span>CHAMPION RUNS</span><h2>Independent model progress</h2></div>
            <span className="tableHint">No global progress bar</span>
          </div>
          <div className="modelRunList">
            {generationSlots.map((slot) => {
              const run = latestRuns.get(slot.modelId);
              const progress = run?.progress_fraction ?? 0;
              const state = slot.frozen ? run?.state ?? "WAITING_FOR_DATA" : "NOT_FROZEN";
              return (
                <article className={`modelRunRow ${slot.frozen ? "" : "futureRun"}`} key={slot.modelId}>
                  <div className="runIdentity">
                    <span className={`generationPill ${slot.generation.toLowerCase()}`}>{slot.generation}</span>
                    <div><strong>{slot.name}</strong><small>{slot.frozen ? slot.modelId : "Muncul otomatis setelah generasi ini punya frozen champion"}</small></div>
                  </div>
                  <div className="runProgressBlock">
                    <div className="runProgressHead"><span>{state.replaceAll("_", " ")}</span>{slot.frozen && <em>{Math.round(progress * 100)}%</em>}</div>
                    <div className={`runTrack ${state === "FAILED" ? "failed" : ""}`}><span style={{ width: `${progress * 100}%` }} /></div>
                  </div>
                  <div className="runMeta">
                    {slot.frozen ? <><span>{v2DoneDates.size}/{slot.targetSessions ?? "—"} sessions</span><strong>{run?.artifact_sha256 ? "Artifact verified" : "Waiting"}</strong></> : <><span>Research generation</span><strong>Not monitorable yet</strong></>}
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="recoveryStrip">
          <span>RECOVERY</span>
          <p><strong>Restart safe:</strong> DATA_READY di-skip, verified DONE model di-skip, dan hanya gap/interrupted unit yang dijalankan ulang.</p>
        </section>

        <div className="pageFooter"><span>IDX Trade · exploratory research only</span><span>Signal-side monitoring only · reserved H10 outcomes remain sealed.</span></div>
      </div>
    </main>
  );
}
