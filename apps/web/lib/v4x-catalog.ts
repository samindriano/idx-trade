export const V4X_ALPHA = {
  id: "V4_X1_GEOMETRY3_PROSPECTIVE",
  shortName: "V4-X Geometry3",
  generation: "V4-X1",
  role: "Current alpha candidate",
  featureCount: 28,
  controlFeatureCount: 25,
  addedFeatures: [
    "session_open_position_range",
    "session_body_signed_range",
    "session_log_high_low_range",
  ] as const,
  forwardTargetSessions: 100,
  modelBundleManifestSha256: "3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094",
  historicalParent: "V4-3R",

  // Frozen V4-3R chart/protocol aggregates. These are medians of six fold-mean
  // daily ICs and are retained so the original historical chart stays exact.
  historicalConsensusIc: 0.09775243938276076,
  historicalControlConsensusIc: 0.08415844149089491,
  historicalH5Ic: 0.07891122009359626,
  historicalH10Ic: 0.09095594288451861,
  historicalConsensusRelativeLift: 0.161534,

  // Preferred audited historical headline: mean daily Spearman after restricting
  // alpha and realized target to identical observable names and reranking both.
  auditedCommonSupportConsensusIc: 0.09545975125676774,
  auditedCommonSupportControlConsensusIc: 0.08979323509925058,
  auditedCommonSupportH5Ic: 0.07493424533009098,
  auditedCommonSupportH10Ic: 0.09185167971133042,
  auditedStrictSupportConsensusIc: 0.08327323251280924,
  auditedStrictSupportRetainedFraction: 0.8996852225456887,
  auditedCommonSupportIncrementalIc: 0.00566651615751716,
  auditedPairedMeanDailyIncrementalIc: 0.005804318872319132,
  auditedPairedMedianFoldIncrementalIc: 0.0062863346170079215,
  auditedPositivePairedConsensusDeltaFolds: 5,
  auditStatus: "PASS_NO_CRITICAL_ERROR_FOUND",
  historicalValidationSessions: 600,

  positiveConsensusFolds: 6,
  foldCount: 6,
  consensusBootstrapLow: 0.07596040021990692,
  consensusBootstrapHigh: 0.12337528363943043,
  incrementalBootstrapLow: 0.0014116604765849416,
  incrementalBootstrapHigh: 0.01005689409146089,
  status: "FROZEN_FORWARD_CONFIRMATION",
} as const;

export const V4X_CONSENSUS_FOLDS = [
  { fold: "F1", geometry3: 0.09227078711981862, control: 0.08158537935780505 },
  { fold: "F2", geometry3: 0.06625356936830826, control: 0.05847989415840352 },
  { fold: "F3", geometry3: 0.1032340916457029, control: 0.08673150362398477 },
  { fold: "F4", geometry3: 0.029696513400161204, control: 0.027476807935605786 },
  { fold: "F5", geometry3: 0.12931364086270405, control: 0.1364680981110922 },
  { fold: "F6", geometry3: 0.16348225628388718, control: 0.15868326225977608 },
] as const;
