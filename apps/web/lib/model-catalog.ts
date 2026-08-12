export type ResearchStatus = "FINAL" | "BASELINE" | "FAIL" | "BLOCKED" | "RESEARCH";
export type ResearchComparisonClass = "V2_BASELINE" | "OPEN_FEATURES" | "V3_VARIANTS" | "V4_VARIANTS" | "RISK";

export type ResearchFoldMetric = {
  fold: string;
  deltaPr: number;
  score?: number;
  roc?: number;
  qSpread?: number;
  supportRows?: number;
};

export type ResearchBaselineFold = {
  fold: string;
  score: number;
  roc: number;
  qSpread: number;
  supportRows: number;
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
  comparisonClass: ResearchComparisonClass;
  name: string;
  candidate: string;
  status: ResearchStatus;
  trackingRole?: "PRIMARY_CHALLENGER" | "INCUMBENT" | "REFERENCE";
  historicalRank?: number;
  result: string;
  note: string;
  evidence?: ResearchEvidence;
  dataBlocker?: boolean;
  keyFindings: readonly string[];
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

export const O2_CHALLENGER = {
  id: "O2-GEOMETRY-FULL3-V1-CANDIDATE-001",
  shortName: "O2 Open Geometry",
  generation: "O2",
  featureCount: 36,
  finalRefitRows: 278168,
  finalRefitTickers: 729,
  modelSha256: "42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb",
  manifestSha256: "535875e74a1b3a6532e95addf819521758798a767bc49ee9b30d54054a0ae7c2",
  featureOrderSha256: "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f",
  historicalMedianPairedDeltaPr: 0.007276,
  historicalPositiveFolds: 6,
  historicalFoldCount: 6,
  forwardTargetSessions: 100,
} as const;

export const V3_B_DISCOVERY_FOLDS = [
  { fold: "F1", deltaPr: 0.007948, roc: 0.002743, qSpread: 0.013084 },
  { fold: "F2", deltaPr: 0.001841, roc: 0.009782, qSpread: 0.015608 },
  { fold: "F3", deltaPr: 0.004879, roc: 0.001502, qSpread: 0.009564 },
  { fold: "F4", deltaPr: 0.002973, roc: 0.001748, qSpread: 0.005156 },
] as const;

// Certified common-support reference used by the O1/O2 comparator:
// 278,168 rows, 729 tickers, six chronological folds.
export const V3_B_COMMON_SUPPORT_FOLDS: readonly ResearchBaselineFold[] = [
  { fold: "F1", score: 0.41165279091300033, roc: 0.5343002825747942, qSpread: 0.0882508795853264, supportRows: 21501 },
  { fold: "F2", score: 0.41079850777744475, roc: 0.5283766367167901, qSpread: 0.07589875062194207, supportRows: 20057 },
  { fold: "F3", score: 0.4196648421332274, roc: 0.5251739451875269, qSpread: 0.05360409218120221, supportRows: 20272 },
  { fold: "F4", score: 0.4285662266379463, roc: 0.5219320824401948, qSpread: 0.048682040735453236, supportRows: 20205 },
  { fold: "F5", score: 0.4895739884224322, roc: 0.5344351611116392, qSpread: 0.03701738761434964, supportRows: 25347 },
  { fold: "F6", score: 0.33643067776932933, roc: 0.4858364626648122, qSpread: 0.04282583108228749, supportRows: 33297 },
] as const;

const V2_CHAMPION_FOLDS = [
  { fold: "F1", deltaPr: 0.0216774918 },
  { fold: "F2", deltaPr: 0.0289990901 },
  { fold: "F3", deltaPr: 0.0087894853 },
  { fold: "F4", deltaPr: 0.0382948851 },
  { fold: "F5", deltaPr: 0.0260816692 },
  { fold: "F6", deltaPr: 0.0186432663 },
] as const;

const O1A_OVERNIGHT_FOLDS = [
  { fold: "F1", deltaPr: -0.0012915880624221887, score: 0.41036120285057814, roc: 0.533723585176148, qSpread: 0.07949108244378655, supportRows: 21501 },
  { fold: "F2", deltaPr: 0.002083571722863109, score: 0.41288207950030786, roc: 0.5277487378661275, qSpread: 0.06930967564794777, supportRows: 20057 },
  { fold: "F3", deltaPr: 0.0016357262691586438, score: 0.42130056840238606, roc: 0.5272993889170631, qSpread: 0.058740743716439725, supportRows: 20272 },
  { fold: "F4", deltaPr: -0.014954853128374412, score: 0.4136113735095719, roc: 0.5103311046603508, qSpread: 0.03844509119444406, supportRows: 20205 },
  { fold: "F5", deltaPr: -0.0016604485083553389, score: 0.4879135399140769, roc: 0.5320162287818554, qSpread: 0.05429201562421898, supportRows: 25347 },
  { fold: "F6", deltaPr: 0.012650399351445463, score: 0.3490810771207748, roc: 0.49639252979029147, qSpread: 0.042924416045320546, supportRows: 33297 },
] as const;

const O1B_INTRADAY_FOLDS = [
  { fold: "F1", deltaPr: 0.002336519507158241, score: 0.4139893104201586, roc: 0.5332969478015114, qSpread: 0.09251286488958704, supportRows: 21501 },
  { fold: "F2", deltaPr: -0.00097840887021039, score: 0.40982009890723436, roc: 0.5272740905730215, qSpread: 0.06701232747360186, supportRows: 20057 },
  { fold: "F3", deltaPr: 0.0021118230849803687, score: 0.4217766652182078, roc: 0.5251545333915235, qSpread: 0.043435236144029776, supportRows: 20272 },
  { fold: "F4", deltaPr: -0.004234156542806622, score: 0.4243320700951397, roc: 0.5123662641488016, qSpread: 0.036673835452006975, supportRows: 20205 },
  { fold: "F5", deltaPr: 0.0015197454710102476, score: 0.49109373389344246, roc: 0.5358698863049236, qSpread: 0.046267109346135205, supportRows: 25347 },
  { fold: "F6", deltaPr: 0.011820542729460981, score: 0.3482512204987903, roc: 0.49239031950441947, qSpread: 0.038928275019756486, supportRows: 33297 },
] as const;

const O1C_DECOMPOSITION_FOLDS = [
  { fold: "F1", deltaPr: 0.000809061057561844, score: 0.4124618519705622, roc: 0.5341362318817163, qSpread: 0.08621950144668428, supportRows: 21501 },
  { fold: "F2", deltaPr: 0.0034989177281643524, score: 0.4142974255056091, roc: 0.5298332543877828, qSpread: 0.07199376833587245, supportRows: 20057 },
  { fold: "F3", deltaPr: -0.0009708157295899023, score: 0.4186940264036375, roc: 0.5235068725831474, qSpread: 0.05966202011274924, supportRows: 20272 },
  { fold: "F4", deltaPr: -0.012117987079336312, score: 0.41644823955861, roc: 0.5071783158688737, qSpread: 0.022899334040170194, supportRows: 20205 },
  { fold: "F5", deltaPr: 0.0038423465194802886, score: 0.4934163349419125, roc: 0.5359567706554096, qSpread: 0.06480246590840283, supportRows: 25347 },
  { fold: "F6", deltaPr: 0.025484700438496044, score: 0.3619153782078254, roc: 0.5060294678173356, qSpread: 0.04501659551126341, supportRows: 33297 },
] as const;

const O2_OPEN_GEOMETRY_FOLDS = [
  { fold: "F1", deltaPr: 0.0038655063957908076, score: 0.41551829730879114, roc: 0.5375533518191322, qSpread: 0.08903339489943374, supportRows: 21501 },
  { fold: "F2", deltaPr: 0.00045111340321468685, score: 0.41124962118065944, roc: 0.5295545518781186, qSpread: 0.09383945758569257, supportRows: 20057 },
  { fold: "F3", deltaPr: 0.007242060826206376, score: 0.4269069029594338, roc: 0.5356642833434203, qSpread: 0.056654481179448046, supportRows: 20272 },
  { fold: "F4", deltaPr: 0.007310380993454935, score: 0.43587660763140124, roc: 0.5277116139372107, qSpread: 0.042159597196066934, supportRows: 20205 },
  { fold: "F5", deltaPr: 0.01203124575284159, score: 0.5016052341752738, roc: 0.5408824464318686, qSpread: 0.08119570718760244, supportRows: 25347 },
  { fold: "F6", deltaPr: 0.013822826689179724, score: 0.35025350445850906, roc: 0.4966297091489187, qSpread: 0.04191637803355652, supportRows: 33297 },
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
    comparisonClass: "V2_BASELINE",
    name: "HGB XS + Market",
    candidate: "HGB_XS_MARKET",
    status: "BASELINE",
    trackingRole: "REFERENCE",
    historicalRank: 3,
    result: "Historical V2 champion",
    note: "Median ΔPR +2.39%, median ROC 0.5244, median Q5−Q1 +5.12% across six folds.",
    keyFindings: [
      "PR-AUC delta stayed positive across all six development folds.",
      "Median PR-AUC delta was +2.39% with median ROC-AUC 0.5244.",
      "Selected as the historical V2 champion; fresh-forward validation remains separate.",
    ],
    evidence: {
      metricLabel: "PR-AUC delta vs base rate",
      caption: "Six historical development folds from the selected V2 champion.",
      series: [{ label: "HGB XS + Market", points: V2_CHAMPION_FOLDS }],
    },
  },
  {
    generation: "V3-A",
    comparisonClass: "V3_VARIANTS",
    name: "Recency weighting",
    candidate: "H252 / H504",
    status: "FAIL",
    result: "Killed",
    note: "Both recency variants failed the paired promotion gate; no rescue.",
    keyFindings: [
      "Both recency variants showed late-fold deterioration.",
      "The paired promotion gate was not satisfied consistently.",
      "The candidate was stopped without rescue or further tuning.",
    ],
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
    comparisonClass: "V3_VARIANTS",
    name: "Structure-Lite",
    candidate: FINAL_RANKER.id,
    status: "FINAL",
    trackingRole: "INCUMBENT",
    historicalRank: 2,
    result: "Promoted + late confirmation PASS",
    note: "Only surviving V3 component. Exact V2 information set plus eight causal price-geometry features.",
    keyFindings: [
      "Paired PR-AUC improved across every F1-F4 discovery fold.",
      "The structure-lite feature family was the only surviving V3 component.",
      "Late confirmation also passed under the frozen promotion process.",
    ],
    evidence: {
      metricLabel: "Paired PR-AUC delta vs V2",
      caption: "Paired discovery PR-AUC improved across every F1-F4 fold.",
      series: [{ label: "V3-B / V2", points: V3_B_DISCOVERY_FOLDS }],
    },
  },
  {
    generation: "O1",
    comparisonClass: "OPEN_FEATURES",
    name: "Raw Open features",
    candidate: "O1A / O1B / O1C",
    status: "FAIL",
    result: "No survivor",
    note: "Overnight-gap, intraday-return, and decomposition variants all failed the frozen lower-quartile paired-improvement gate.",
    keyFindings: [
      "O1A, O1B, and O1C did not produce a robust survivor.",
      "The strongest median uplift was only +0.215%, with a negative lower quartile.",
      "O1 was closed without rescue or post-hoc tuning.",
    ],
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "All three O1 Open variants are shown across the six historical development folds.",
      series: [
        { label: "O1A overnight", points: O1A_OVERNIGHT_FOLDS },
        { label: "O1B intraday", points: O1B_INTRADAY_FOLDS },
        { label: "O1C decomposition", points: O1C_DECOMPOSITION_FOLDS },
      ],
    },
  },
  {
    generation: "O2",
    comparisonClass: "OPEN_FEATURES",
    name: "Open Geometry",
    candidate: O2_CHALLENGER.id,
    status: "RESEARCH",
    trackingRole: "PRIMARY_CHALLENGER",
    historicalRank: 1,
    result: "Primary challenger · 6/6 historical folds",
    note: "Full three-feature Open geometry is the strongest historical challenger, but it remains unpromoted until its separate 100-session fresh-forward gate completes.",
    keyFindings: [
      "Paired PR-AUC uplift was positive in all six historical folds.",
      "Median paired PR-AUC delta was +0.7276%; lower quartile was +0.4710%.",
      "O2 is tracked against the unchanged V3-B incumbent on identical forward sessions.",
    ],
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "O2 Open Geometry is the primary historical challenger; fresh-forward validation remains separate.",
      series: [{ label: "O2 Open Geometry", points: O2_OPEN_GEOMETRY_FOLDS }],
    },
  },
  {
    generation: "V3-C",
    comparisonClass: "V3_VARIANTS",
    name: "Regime specialization",
    candidate: "TWO-EXPERT-007",
    status: "FAIL",
    result: "Killed",
    note: "Overall median paired ΔPR −1.23%; stress regime degraded materially.",
    keyFindings: [
      "The candidate underperformed its control in three of four folds.",
      "Stress-regime performance degraded materially.",
      "Median paired PR-AUC change was −1.23%.",
    ],
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "The regime-specialization candidate falls below its control in three of four folds.",
      series: [{ label: "Two-expert", points: V3_C_FOLDS }],
    },
  },
  {
    generation: "V3-D",
    comparisonClass: "V3_VARIANTS",
    name: "Sector relative",
    candidate: "008 / 009",
    status: "BLOCKED",
    result: "PIT data blocked",
    note: "No defensible historical ticker-by-date IDX-IC membership chain; outcomes remain unviewed.",
    dataBlocker: true,
    keyFindings: [
      "Historical ticker-by-date IDX-IC membership could not be reconstructed defensibly.",
      "The candidate was blocked before a valid performance comparison.",
      "No performance conclusion was drawn from the incomplete PIT data.",
    ],
  },
  {
    generation: "V3-E",
    comparisonClass: "V3_VARIANTS",
    name: "True ranking / LambdaMART",
    candidate: "LAMBDAMART-011",
    status: "FAIL",
    result: "Killed",
    note: "Some PR uplift, but robustness and Q5−Q1 promotion gates failed.",
    keyFindings: [
      "Early folds showed PR-AUC uplift against the control.",
      "The final discovery fold reversed negative.",
      "Robustness and Q5-Q1 promotion gates failed.",
    ],
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "LambdaMART's PR-AUC improvement reversed in the final discovery fold.",
      series: [{ label: "LambdaMART", points: V3_E_FOLDS }],
    },
  },
  {
    generation: "V4-A",
    comparisonClass: "V4_VARIANTS",
    name: "Participation quality",
    candidate: "013 / 014",
    status: "FAIL",
    result: "No survivor",
    note: "Impact/Absorption and Persistent Directional Participation both failed.",
    keyFindings: [
      "Neither participation candidate survived the full gate.",
      "Both candidates showed weakness in later development folds.",
      "No participation variant was promoted.",
    ],
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
    comparisonClass: "V4_VARIANTS",
    name: "Price-path quality",
    candidate: "016 / 017",
    status: "FAIL",
    result: "No survivor",
    note: "Coherence failed; Range Acceptance had positive aggregate uplift but failed late-fold protection.",
    keyFindings: [
      "Coherence produced mixed results and failed its robustness gate.",
      "Range Acceptance had aggregate uplift but failed late-fold protection.",
      "Neither price-path candidate survived promotion.",
    ],
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
    comparisonClass: "V4_VARIANTS",
    name: "Cross-sectional dispersion",
    candidate: "019",
    status: "FAIL",
    result: "No survivor",
    note: "Median paired ΔPR +0.147% missed the +0.150% gate and other robustness gates also failed.",
    keyFindings: [
      "Early folds were positive, but the final fold reversed negative.",
      "Median paired PR-AUC delta was +0.147%, below the +0.150% gate.",
      "Additional robustness gates also failed.",
    ],
    evidence: {
      metricLabel: "Paired PR-AUC change vs V3-B",
      caption: "Cross-sectional dispersion shows a strong early profile but reverses in the final fold.",
      series: [{ label: "Dispersion", points: V4_C_FOLDS }],
    },
  },
  {
    generation: "Risk",
    comparisonClass: "RISK",
    name: "Path Risk V1",
    candidate: "PATH-RISK-A-Q75-HGB-001",
    status: "FAIL",
    result: "Discovery FAIL_CLOSE",
    note: "Ordering diagnostics were positive, but q75 pinball robustness failed the frozen gate; no F5/F6, rescue, or alpha+risk integration.",
    dataBlocker: true,
    keyFindings: [
      "Ordering diagnostics were directionally positive.",
      "q75 pinball robustness failed the frozen gate.",
      "No F5/F6 expansion, rescue, or alpha-plus-risk integration was allowed.",
    ],
  },
];
