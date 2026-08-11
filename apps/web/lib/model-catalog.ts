export type ResearchStatus = "FINAL" | "BASELINE" | "FAIL" | "BLOCKED" | "RESEARCH";

export type ResearchFoldMetric = {
  fold: string;
  deltaPr: number;
  roc?: number;
  qSpread?: number;
};

export type ResearchEvidenceSeries = {
  label: string;
  points: readonly ResearchFoldMetric[];
};

export type ResearchEvidence = {
  metricLabel: string;
  caption: string;
  series: readonly ResearchEvidenceSeries[];
};

export type ResearchExperiment = {
  generation: string;
  name: string;
  candidate: string;
  status: ResearchStatus;
  result: string;
  note: string;
  evidence?: ResearchEvidence;
  dataBlocker?: boolean;
};

export const FINAL_RANKER = {
  id: "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005",
  shortName: "V3-B Structure-Lite",
  generation: "V3",
  featureCount: 33,
  finalRefitRows: 292633,
  finalRefitTickers: 737,
  finalRefitSessions: "20..1250",
  modelSha256: "1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6",
  manifestSha256: "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9",
  featureOrderSha256: "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e",
  discoveryMedianPairedDeltaPr: 0.003925845,
  lateMedianPairedDeltaPr: 0.0075911303,
  lateWorstPairedDeltaPr: 0.0016661426,
  forwardTargetSessions: 100,
  forwardCutoff: "2026-07-31",
} as const;

export const V2_CHAMPION = {
  id: "HGB_XS_MARKET",
  shortName: "HGB XS + Market",
  generation: "V2",
  featureCount: 25,
  modelSha256: "5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace",
  manifestSha256: "f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9",
  forwardTargetSessions: 100,
} as const;

export const V3_B_DISCOVERY_FOLDS = [
  { fold: "F1", deltaPr: 0.007948, roc: 0.002743, qSpread: 0.013084 },
  { fold: "F2", deltaPr: 0.001841, roc: 0.009782, qSpread: 0.015608 },
  { fold: "F3", deltaPr: 0.004879, roc: 0.001502, qSpread: 0.009564 },
  { fold: "F4", deltaPr: 0.002973, roc: 0.001748, qSpread: 0.005156 },
] as const;

const V2_CHAMPION_FOLDS = [
  { fold: "F1", deltaPr: 0.0216774918 },
  { fold: "F2", deltaPr: 0.0289990901 },
  { fold: "F3", deltaPr: 0.0087894853 },
  { fold: "F4", deltaPr: 0.0382948851 },
  { fold: "F5", deltaPr: 0.0260816692 },
  { fold: "F6", deltaPr: 0.0186432663 },
] as const;

const V3_A_H252_FOLDS = [
  { fold: "F1", deltaPr: 0.0075943698 },
  { fold: "F2", deltaPr: 0.0059093010 },
  { fold: "F3", deltaPr: -0.0062116193 },
  { fold: "F4", deltaPr: -0.0091929210 },
] as const;

const V3_A_H504_FOLDS = [
  { fold: "F1", deltaPr: 0.0051240318 },
  { fold: "F2", deltaPr: 0.0019016524 },
  { fold: "F3", deltaPr: -0.0017879420 },
  { fold: "F4", deltaPr: -0.0345301016 },
] as const;

const V3_C_FOLDS = [
  { fold: "F1", deltaPr: -0.0111186352 },
  { fold: "F2", deltaPr: -0.0221428730 },
  { fold: "F3", deltaPr: 0.0222075419 },
  { fold: "F4", deltaPr: -0.0135157431 },
] as const;

const V3_E_FOLDS = [
  { fold: "F1", deltaPr: 0.0061055536 },
  { fold: "F2", deltaPr: 0.0037787365 },
  { fold: "F3", deltaPr: 0.0191587603 },
  { fold: "F4", deltaPr: -0.0253353754 },
] as const;

const V4_A_IMPACT_FOLDS = [
  { fold: "F1", deltaPr: 0.0040161320 },
  { fold: "F2", deltaPr: 0.0015336871 },
  { fold: "F3", deltaPr: -0.0013733281 },
  { fold: "F4", deltaPr: 0.0022205772 },
  { fold: "F5", deltaPr: -0.0014500930 },
  { fold: "F6", deltaPr: -0.0116775888 },
] as const;

const V4_A_PERSISTENCE_FOLDS = [
  { fold: "F1", deltaPr: 0.0034991328 },
  { fold: "F2", deltaPr: 0.0021464711 },
  { fold: "F3", deltaPr: -0.0053115173 },
  { fold: "F4", deltaPr: -0.0072388702 },
  { fold: "F5", deltaPr: 0.0014138400 },
  { fold: "F6", deltaPr: 0.0006198268 },
] as const;

const V4_B_COHERENCE_FOLDS = [
  { fold: "F1", deltaPr: 0.0024449252 },
  { fold: "F2", deltaPr: 0.0027391273 },
  { fold: "F3", deltaPr: -0.0043080206 },
  { fold: "F4", deltaPr: -0.0114229736 },
  { fold: "F5", deltaPr: 0.0013810536 },
  { fold: "F6", deltaPr: -0.0032163378 },
] as const;

const V4_B_RANGE_FOLDS = [
  { fold: "F1", deltaPr: 0.0103945841 },
  { fold: "F2", deltaPr: 0.0218949329 },
  { fold: "F3", deltaPr: -0.0014045382 },
  { fold: "F4", deltaPr: 0.0032085928 },
  { fold: "F5", deltaPr: 0.0039737952 },
  { fold: "F6", deltaPr: -0.0097175361 },
] as const;

const V4_C_FOLDS = [
  { fold: "F1", deltaPr: 0.0102384577 },
  { fold: "F2", deltaPr: 0.0023095349 },
  { fold: "F3", deltaPr: -0.0072453235 },
  { fold: "F4", deltaPr: 0.0006307876 },
  { fold: "F5", deltaPr: 0.0085398031 },
  { fold: "F6", deltaPr: -0.0265794272 },
] as const;

export const RESEARCH_EXPERIMENTS: ResearchExperiment[] = [
  {
    generation: "V2",
    name: "HGB XS + Market",
    candidate: "HGB_XS_MARKET",
    status: "BASELINE",
    result: "Historical V2 champion",
    note: "Median ΔPR +2.39%, median ROC 0.5244, median Q5−Q1 +5.12% across six folds.",
    evidence: {
      metricLabel: "PR-AUC delta vs base rate",
      caption: "Six historical development folds from the selected V2 champion.",
      series: [{ label: "HGB XS + Market", points: V2_CHAMPION_FOLDS }],
    },
  },
  {
    generation: "V3-A",
    name: "Recency weighting",
    candidate: "H252 / H504",
    status: "FAIL",
    result: "Killed",
    note: "Both recency variants failed the paired promotion gate; no rescue.",
    evidence: {
      metricLabel: "Paired PR-AUC change vs V2",
      caption: "The two recency variants are shown together across the four discovery folds.",
      series: [
        { label: "H252", points: V3_A_H252_FOLDS },
        { label: "H504", points: V3_A_H504_FOLDS },
      ],
    },
  },
  {
    generation: "V3-B",
    name: "Structure-Lite",
    candidate: FINAL_RANKER.id,
    status: "FINAL",
    result: "Promoted + late confirmation PASS",
    note: "Only surviving V3 component. Exact V2 information set plus eight causal price-geometry features.",
    evidence: {
      metricLabel: "Paired PR-AUC delta vs V2",
      caption: "Paired discovery PR-AUC improved across every F1-F4 fold.",
      series: [{ label: "V3-B / V2", points: V3_B_DISCOVERY_FOLDS }],
    },
  },
  {
    generation: "V3-C",
    name: "Regime specialization",
    candidate: "TWO-EXPERT-007",
    status: "FAIL",
    result: "Killed",
    note: "Overall median paired ΔPR −1.23%; stress regime degraded materially.",
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "The regime-specialization candidate falls below its control in three of four folds.",
      series: [{ label: "Two-expert", points: V3_C_FOLDS }],
    },
  },
  {
    generation: "V3-D",
    name: "Sector relative",
    candidate: "008 / 009",
    status: "BLOCKED",
    result: "PIT data blocked",
    note: "No defensible historical ticker-by-date IDX-IC membership chain; outcomes remain unviewed.",
    dataBlocker: true,
  },
  {
    generation: "V3-E",
    name: "True ranking / LambdaMART",
    candidate: "LAMBDAMART-011",
    status: "FAIL",
    result: "Killed",
    note: "Some PR uplift, but robustness and Q5−Q1 promotion gates failed.",
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "LambdaMART's PR-AUC improvement reversed in the final discovery fold.",
      series: [{ label: "LambdaMART", points: V3_E_FOLDS }],
    },
  },
  {
    generation: "V4-A",
    name: "Participation quality",
    candidate: "013 / 014",
    status: "FAIL",
    result: "No survivor",
    note: "Impact/Absorption and Persistent Directional Participation both failed.",
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "Both participation candidates are shown across the six development folds.",
      series: [
        { label: "Impact", points: V4_A_IMPACT_FOLDS },
        { label: "Persistent direction", points: V4_A_PERSISTENCE_FOLDS },
      ],
    },
  },
  {
    generation: "V4-B",
    name: "Price-path quality",
    candidate: "016 / 017",
    status: "FAIL",
    result: "No survivor",
    note: "Coherence failed; Range Acceptance had positive aggregate uplift but failed late-fold protection.",
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "The two price-path candidates are shown together; late-fold weakness remains visible.",
      series: [
        { label: "Coherence", points: V4_B_COHERENCE_FOLDS },
        { label: "Range acceptance", points: V4_B_RANGE_FOLDS },
      ],
    },
  },
  {
    generation: "V4-C",
    name: "Cross-sectional dispersion",
    candidate: "019",
    status: "FAIL",
    result: "No survivor",
    note: "Median paired ΔPR +0.147% missed the +0.150% gate and other robustness gates also failed.",
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "Cross-sectional dispersion shows a strong early profile but reverses in the final fold.",
      series: [{ label: "Dispersion", points: V4_C_FOLDS }],
    },
  },
  {
    generation: "Risk",
    name: "Path Risk V1",
    candidate: "PATH-RISK-A-Q75-HGB-001",
    status: "FAIL",
    result: "Discovery FAIL_CLOSE",
    note: "Ordering diagnostics were positive, but q75 pinball robustness failed the frozen gate; no F5/F6, rescue, or alpha+risk integration.",
    dataBlocker: true,
  },
];
