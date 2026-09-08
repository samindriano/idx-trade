#!/usr/bin/env node

import { readFileSync, writeFileSync } from 'node:fs';
import { isAbsolute, resolve } from 'node:path';

import {
  CANDIDATE_MANIFEST_SCHEMA,
  canonicalJson,
  sha256Bytes,
} from '../src/candidate_manifest.mjs';
import {
  DEPLOYMENT_ALLOCATION_ATTESTATION_SCHEMA,
  DIRECT_VERSION_BYTE_ATTESTATION_PROVEN,
  verifyExactDeploymentAllocation,
  verifyVersionModulesAgainstCandidate,
} from '../src/version_attestation.mjs';

const RECEIPT_SCHEMA = 'IDX-CLOUDFLARE-DEPLOYMENT-RECEIPT-V2';

function usage() {
  console.error([
    'Usage: node scripts/generate-deployment-receipt.mjs',
    '  --manifest <generated candidate identity manifest>',
    '  --raw-deployment-response <raw deployments API JSON>',
    '  --raw-version-response <raw Version API JSON>',
    '  --version-id <exact uploaded Version ID>',
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

function rawJson(path, code) {
  if (!path) throw new Error(`${code}_REQUIRED`);
  const bytes = readFileSync(path);
  return { bytes, value: JSON.parse(bytes.toString('utf8')) };
}

const args = argsFrom(process.argv.slice(2));
const required = ['--manifest', '--raw-deployment-response', '--raw-version-response', '--version-id', '--out'];
if (args.has('--help') || required.some((name) => !args.has(name))) {
  usage();
  process.exitCode = args.has('--help') ? 0 : 2;
} else {
  const manifest = JSON.parse(readFileSync(pathArg(args.get('--manifest')), 'utf8'));
  const deployment = rawJson(pathArg(args.get('--raw-deployment-response')), 'RAW_DEPLOYMENT_RESPONSE');
  const version = rawJson(pathArg(args.get('--raw-version-response')), 'RAW_VERSION_RESPONSE');
  const expectedVersionId = args.get('--version-id');
  if (manifest.schema_version !== CANDIDATE_MANIFEST_SCHEMA) throw new Error('CANDIDATE_MANIFEST_SCHEMA_INVALID');
  if (!manifest.compiled_module_set_sha256 || !Array.isArray(manifest.compiled_modules)) throw new Error('CANDIDATE_MODULE_SET_REQUIRED');
  if (typeof manifest.worker_name !== 'string' || typeof manifest.compiled_main_module !== 'string') throw new Error('CANDIDATE_MANIFEST_IDENTITY_INVALID');
  const candidateManifestSha256 = sha256Bytes(Buffer.from(canonicalJson(manifest), 'utf8'));

  const byteAttestation = verifyVersionModulesAgainstCandidate({
    candidateModuleSet: {
      main_module: manifest.compiled_main_module,
      modules: manifest.compiled_modules,
      module_set_sha256: manifest.compiled_module_set_sha256,
    },
    rawVersionResponse: version.value,
    rawResponseBytes: version.bytes,
    expectedWorkerName: manifest.worker_name,
    expectedVersionId,
  });
  if (!byteAttestation.ok) throw new Error(`DIRECT_VERSION_BYTE_ATTESTATION_BLOCKED:${canonicalJson(byteAttestation.issues)}`);

  const allocation = verifyExactDeploymentAllocation({
    rawDeploymentResponse: deployment.value,
    rawResponseBytes: deployment.bytes,
    attestedVersionId: expectedVersionId,
  });
  if (!allocation.ok) throw new Error(`EXACT_DEPLOYMENT_ALLOCATION_BLOCKED:${canonicalJson(allocation.issues)}`);

  const receipt = {
    schema_version: RECEIPT_SCHEMA,
    candidate_manifest_schema: CANDIDATE_MANIFEST_SCHEMA,
    candidate_manifest_sha256: candidateManifestSha256,
    worker_name: manifest.worker_name,
    version_id: expectedVersionId,
    version_number: byteAttestation.version.number,
    version_created_on: byteAttestation.version.created_on,
    version_annotations: byteAttestation.version.annotations,
    main_module: byteAttestation.version.main_module,
    compiled_module_set_sha256: manifest.compiled_module_set_sha256,
    compiled_modules: manifest.compiled_modules,
    direct_version_byte_attestation: DIRECT_VERSION_BYTE_ATTESTATION_PROVEN,
    raw_version_response_sha256: byteAttestation.version.raw_response_sha256,
    deployment_id: allocation.deployment.id,
    deployment_allocation_attestation: DEPLOYMENT_ALLOCATION_ATTESTATION_SCHEMA,
    raw_deployment_response_sha256: allocation.raw_response_sha256,
    traffic_percentage: 100,
    remote_script_etag: byteAttestation.version.resources?.script?.etag,
    source: 'generated-from-raw-cloudflare-version-and-deployment-api',
  };
  writeFileSync(pathArg(args.get('--out')), `${canonicalJson(receipt)}\n`, 'utf8');
  console.log(JSON.stringify({ status: 'DEPLOYMENT_IDENTITY_RECEIPT_V2_GENERATED', path: pathArg(args.get('--out')), receipt }, null, 2));
}
