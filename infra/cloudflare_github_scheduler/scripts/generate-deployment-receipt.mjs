#!/usr/bin/env node

import { readFileSync, writeFileSync } from 'node:fs';
import { isAbsolute, resolve } from 'node:path';

import { CANDIDATE_MANIFEST_SCHEMA, canonicalJson, sha256Bytes } from '../src/candidate_manifest.mjs';

const RECEIPT_SCHEMA = 'IDX-CLOUDFLARE-DEPLOYMENT-RECEIPT-V1';
const SHA256 = /^[0-9a-f]{64}$/;

function usage() {
  console.error([
    'Usage: node scripts/generate-deployment-receipt.mjs',
    '  --manifest <generated candidate identity manifest>',
    '  --deployment-list <wrangler deployments list --json>',
    '  --version-view <wrangler versions view --json>',
    '  --out <receipt JSON>',
  ].join('\n'));
}

function argsFrom(argv) {
  const args = new Map();
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith('--')) continue;
    const next = argv[index + 1];
    if (next && !next.startsWith('--')) { args.set(item, next); index += 1; }
    else args.set(item, true);
  }
  return args;
}

function pathArg(value) {
  return typeof value === 'string' ? (isAbsolute(value) ? value : resolve(process.cwd(), value)) : null;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

const args = argsFrom(process.argv.slice(2));
if (args.has('--help') || !args.has('--manifest') || !args.has('--deployment-list') || !args.has('--version-view') || !args.has('--out')) {
  usage();
  process.exitCode = args.has('--help') ? 0 : 2;
} else {
  const manifestPath = pathArg(args.get('--manifest'));
  const deploymentPath = pathArg(args.get('--deployment-list'));
  const versionPath = pathArg(args.get('--version-view'));
  const outPath = pathArg(args.get('--out'));
  const manifest = readJson(manifestPath);
  const deployments = readJson(deploymentPath);
  const version = readJson(versionPath);
  if (manifest.schema_version !== CANDIDATE_MANIFEST_SCHEMA) throw new Error('CANDIDATE_MANIFEST_SCHEMA_INVALID');
  if (typeof manifest.worker_name !== 'string' || typeof manifest.entrypoint !== 'string') {
    throw new Error('CANDIDATE_MANIFEST_IDENTITY_INVALID');
  }
  const list = Array.isArray(deployments) ? deployments : deployments.deployments;
  const matches = (list ?? []).filter((deployment) => deployment?.versions?.some((entry) => entry.version_id === version.id));
  if (!version.id || matches.length !== 1) throw new Error('DEPLOYMENT_RECEIPT_VERSION_MAPPING_AMBIGUOUS');
  const deployment = matches[0];
  const remoteBundleSha256 = version.resources?.script?.sha256;
  const remoteBundleSizeBytes = version.resources?.script?.size_bytes;
  if (!SHA256.test(remoteBundleSha256 ?? '')
    || !Number.isInteger(remoteBundleSizeBytes)
    || remoteBundleSizeBytes <= 0) {
    throw new Error('RAW_BUNDLE_CONTENT_IDENTITY_REQUIRED');
  }
  if (remoteBundleSha256 !== manifest.compiled_bundle_sha256
    || remoteBundleSizeBytes !== manifest.compiled_bundle_size_bytes) {
    throw new Error('DEPLOYED_BUNDLE_IDENTITY_MISMATCH');
  }
  const receipt = {
    schema_version: RECEIPT_SCHEMA,
    candidate_manifest_schema: CANDIDATE_MANIFEST_SCHEMA,
    candidate_manifest_sha256: sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8')),
    worker_name: manifest.worker_name,
    version_id: version.id,
    deployment_id: deployment.id,
    bundle_sha256: manifest.compiled_bundle_sha256,
    bundle_size_bytes: manifest.compiled_bundle_size_bytes,
    config_sha256: manifest.config_sha256,
    manifest_sha256: sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8')),
    entrypoint: manifest.entrypoint,
    remote_script_etag: version.resources?.script?.etag,
    source: 'generated-from-wrangler-json-readback',
  };
  writeFileSync(outPath, `${canonicalJson(receipt)}\n`, 'utf8');
  console.log(JSON.stringify({ status: 'DEPLOYMENT_IDENTITY_RECEIPT_GENERATED', path: outPath, receipt }, null, 2));
}
