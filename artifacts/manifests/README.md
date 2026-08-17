# Git-owned manifests

Store only small, accepted manifests and hash/provenance records here. Raw
payloads and large derived artifacts remain under the configured external root.

The 126-session data-gate promotion uses
`idx_data_gate_126_certified_snapshot.pointer.json` as a scrubbed pointer to
the external certified snapshot manifest. The certified Parquet panel and
the original absolute-path manifest remain external.
