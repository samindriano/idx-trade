#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, isAbsolute, resolve } from 'node:path';

import {
  PRODUCTION_CANARY_SCOPE,
  PRODUCTION_CRONS,
  validateBundleIdentity,
  validateBundleSource,
  validateDeploymentConfig,
  validateDeploymentReadback,
} from '../src/deployment_readiness.mjs';

function usage() {
  console.error([
    'Usage: node scripts/check-deployment-readiness.mjs',
    '  --config <wrangler jsonc>',
    '  [--bundle <compiled bundle>]',
    '  [--profile production|preparation|staging-live]',
    '  [--expected-bundle-sha256 <sha256>]',
    '  [--expected-version-id <version id> --readback <normalized readback json>]',
  ].join('\n'));
}

function argsFrom(argv) {
  const args = new Map();
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith('--')) continue;
    const next = argv[index + 1];
    if (next && !next.startsWith('--')) {
      args.set(item, next);
      index += 1;
    } else {
      args.set(item, true);
    }
  }
  return args;
}

function stripJsonComments(text) {
  let output = '';
  let inString = false;
  let escaped = false;
  let lineComment = false;
  let blockComment = false;
  for (let index = 0; index < text.length; index += 1) {
    const current = text[index];
    const next = text[index + 1];
    if (lineComment) {
      if (current === '\n') {
        lineComment = false;
        output += current;
      }
      continue;
    }
    if (blockComment) {
      if (current === '*' && next === '/') {
        blockComment = false;
        index += 1;
      } else if (current === '\n') {
        output += current;
      }
      continue;
    }
    if (inString) {
      output += current;
      if (escaped) escaped = false;
      else if (current === '\\') escaped = true;
      else if (current === '"') inString = false;
      continue;
    }
    if (current === '"') {
      inString = true;
      output += current;
    } else if (current === '/' && next === '/') {
      lineComment = true;
      index += 1;
    } else if (current === '/' && next === '*') {
      blockComment = true;
      index += 1;
    } else {
      output += current;
    }
  }
  return output.replace(/,\s*([}\]])/g, '$1');
}

function readJsonc(path) {
  return JSON.parse(stripJsonComments(readFileSync(path, 'utf8')));
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function pathArg(value, baseDir) {
  if (typeof value !== 'string') return null;
  return isAbsolute(value) ? value : resolve(baseDir, value);
}

const args = argsFrom(process.argv.slice(2));
if (args.has('--help') || !args.has('--config')) {
  usage();
  process.exitCode = args.has('--help') ? 0 : 2;
} else {
  const configPath = pathArg(args.get('--config'), process.cwd());
  const configDir = dirname(configPath);
  const profile = args.get('--profile') || 'production';
  const config = readJsonc(configPath);
  const mode = config?.vars?.DISPATCH_MODE;
  const expectedScope = profile === 'production' && mode === 'active'
    ? PRODUCTION_CANARY_SCOPE
    : null;
  const expectedCrons = profile === 'production' && mode === 'active'
    ? PRODUCTION_CRONS
    : profile === 'preparation'
      ? []
      : null;
  const configReport = validateDeploymentConfig(config, {
    profile,
    expectedScope,
    expectedCrons,
  });

  const bundlePath = pathArg(
    args.get('--bundle') || config.main,
    configDir,
  );
  const bundleBytes = readFileSync(bundlePath);
  const bundleSource = bundleBytes.toString('utf8');
  const bundleSha256 = sha256(bundleBytes);
  const bundleIdentity = validateBundleIdentity({
    actualSha256: bundleSha256,
    actualSizeBytes: bundleBytes.length,
    expectedSha256: args.get('--expected-bundle-sha256') || null,
  });
  const bundleReport = {
    ...validateBundleSource(bundleSource, { entrypoint: config.main }),
    ...bundleIdentity,
    path: bundlePath,
  };

  let readbackReport = null;
  const readbackPath = args.get('--readback');
  if (readbackPath) {
    const readback = JSON.parse(readFileSync(pathArg(readbackPath, process.cwd()), 'utf8'));
    readbackReport = validateDeploymentReadback(readback, {
      workerName: config.name,
      versionId: args.get('--expected-version-id'),
      bundleSha256,
      bundleSizeBytes: bundleBytes.length,
      mode,
      allowedSlotIds: typeof config?.vars?.RECOVERY_ALLOWED_SLOTS === 'string'
        ? configReport.scope.allowedSlotIds
        : [],
      crons: configReport.crons,
    });
  }

  const issues = [
    ...configReport.issues,
    ...bundleReport.issues,
    ...(readbackReport?.issues ?? []),
  ];
  const report = {
    status: issues.length === 0 ? 'READY' : 'BLOCKED',
    config: {
      path: configPath,
      sha256: sha256(readFileSync(configPath)),
      worker_name: config.name,
      profile,
      mode,
      required_secret_names: configReport.requiredSecrets,
      allowed_slot_ids: configReport.scope.allowedSlotIds,
      cron_count: configReport.crons?.length ?? null,
    },
    bundle: {
      path: bundlePath,
      size_bytes: bundleBytes.length,
      sha256: bundleSha256,
      entrypoint: config.main,
      scheduled_handler: bundleReport.hasScheduledHandler,
      stub: bundleReport.isStub,
    },
    config_report: configReport,
    bundle_report: bundleReport,
    readback_report: readbackReport,
    issues,
  };
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = issues.length === 0 ? 0 : 1;
}
