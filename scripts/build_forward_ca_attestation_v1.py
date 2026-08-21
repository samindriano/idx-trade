from __future__ import annotations

import argparse

from idx_trade.forward_ca_attestation_v1 import build_attestation, merge_phase_manifests


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    merge = sub.add_parser("merge")
    merge.add_argument("--post-eod-manifest", required=True)
    merge.add_argument("--preopen-manifest", required=True)
    merge.add_argument("--output", required=True)

    build = sub.add_parser("attest")
    build.add_argument("--source-manifest", required=True)
    build.add_argument("--output", required=True)

    args = parser.parse_args()
    if args.command == "merge":
        path = merge_phase_manifests(
            post_eod_manifest_path=args.post_eod_manifest,
            preopen_manifest_path=args.preopen_manifest,
            output_path=args.output,
        )
    else:
        path = build_attestation(
            source_manifest_path=args.source_manifest,
            output_path=args.output,
        )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
