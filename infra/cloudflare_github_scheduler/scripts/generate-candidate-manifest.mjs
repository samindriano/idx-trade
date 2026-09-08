#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, readdirSync, statSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';

import {
  buildCandidateIdentityManifest,
  canonicalJson,
} from '../src/candidate_manifest.mjs';

function usage() {
  console.error([
    'Usage: node scripts/generate-candidate-manifest.mjs',
    '  --config <wrangler jsonc>',
    '  --profile <staging_live_observe_only|production_preparation|production_active_intraday_2030>',
    '  [--bundle <compiled Wrangler bundle>]',
    '  [--modules-dir <compiled Wrangler module directory>]',
    '  [--main-module <compiled main module name>]',
    '  [--manifest-out <output JSON>]',
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
    } else args.set(item, true);
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
      if (current === '\n') { lineComment = false; output += current; }
      continue;
    }
    if (blockComment) {
      if (current === '*' && next === '/') { blockComment = false; index += 1; }
      else if (current === '\n') output += current;
      continue;
    }
    if (inString) {
      output += current;
      if (escaped) escaped = false;
      else if (current === '\\') escaped = true;
      else if (current === '"') inString = false;
      continue;
    }
    if (current === '"') { inString = true; output += current; }
    else if (current === '/' && next === '/') { lineComment = true; index += 1; }
    else if (current === '/' && next === '*') { blockComment = true; index += 1; }
    else output += current;
  }
  return output.replace(/,\s*([}\]])/g, '$1');
}

function pathArg(value, baseDir) {
  if (typeof value !== 'string') return null;
  return isAbsolute(value) ? value : resolve(baseDir, value);
}

function findBundle(root) {
  const candidates = [];
  function visit(directory) {
    for (const name of readdirSync(directory)) {
      const path = join(directory, name);
      const info = statSync(path);
      if (info.isDirectory()) visit(path);
      else if (name === 'index.js') candidates.push(path);
    }
  }
  visit(root);
  if (candidates.length !== 1) throw new Error(`COMPILED_BUNDLE_DISCOVERY_AMBIGUOUS:${candidates.length}`);
  return candidates[0];
}

function contentTypeFor(name) {
  if (/\.(?:js|mjs|cjs)$/i.test(name)) return 'application/javascript+module';
  if (/\.wasm$/i.test(name)) return 'application/wasm';
  if (/\.json$/i.test(name)) return 'application/json';
  if (/\.txt$/i.test(name)) return 'text/plain';
  return 'application/octet-stream';
}

function readCompiledModules(root, bundlePath, mainModule) {
  const paths = [];
  function visit(directory) {
    for (const name of readdirSync(directory)) {
      const path = join(directory, name);
      const info = statSync(path);
      if (info.isDirectory()) visit(path);
      else if (!/^(?:README\.md|meta\.json)$/i.test(name) && !/\.map$/i.test(name)) paths.push(path);
    }
  }
  visit(root);
  if (!paths.length) throw new Error('COMPILED_MODULE_DISCOVERY_EMPTY');
  const bundleResolved = resolve(bundlePath);
  const modules = paths.map((path) => ({
    name: path === bundleResolved ? mainModule : relative(root, path).replaceAll('\\', '/'),
    content_type: contentTypeFor(path),
    bytes: readFileSync(path),
  }));
  if (!modules.some(({ name }) => name === mainModule)) throw new Error('COMPILED_MAIN_MODULE_NOT_FOUND');
  return modules;
}

function gitSha(cwd) {
  return execFileSync('git', ['rev-parse', 'HEAD'], { cwd, encoding: 'utf8' }).trim();
}

function wranglerVersion(cwd) {
  const wranglerEntrypoint = resolve(cwd, 'node_modules/wrangler/bin/wrangler.js');
  const output = execFileSync(process.execPath, [wranglerEntrypoint, '--version'], {
    cwd,
    encoding: 'utf8',
  });
  const versions = output.match(/\d+\.\d+\.\d+/g) ?? [];
  if (!versions.length) throw new Error('WRANGLER_VERSION_UNRESOLVED');
  return versions.at(-1);
}

function assertCandidateInputsClean(repoRoot, configDir) {
  const candidatePath = relative(repoRoot, configDir);
  if (!candidatePath || candidatePath.startsWith('..')) throw new Error('CANDIDATE_CONFIG_OUTSIDE_REPOSITORY');
  const status = execFileSync('git', [
    'status', '--porcelain=v1', '--untracked-files=all', '--', candidatePath,
  ], { cwd: repoRoot, encoding: 'utf8' }).trim();
  if (status) throw new Error('CANDIDATE_INPUT_TREE_DIRTY');
}

const args = argsFrom(process.argv.slice(2));
if (args.has('--help') || !args.has('--config') || !args.has('--profile')) {
  usage();
  process.exitCode = args.has('--help') ? 0 : 2;
} else {
  const configPath = pathArg(args.get('--config'), process.cwd());
  const configDir = dirname(configPath);
  const configRaw = readFileSync(configPath);
  const config = JSON.parse(stripJsonComments(configRaw.toString('utf8')));
  const repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: configDir, encoding: 'utf8' }).trim();
  assertCandidateInputsClean(repoRoot, configDir);
  let bundlePath = pathArg(args.get('--bundle'), configDir);
  const mainModule = typeof args.get('--main-module') === 'string' ? args.get('--main-module') : 'index.js';
  let generated = false;
  let tempRoot = null;
  try {
    if (!bundlePath) {
      generated = true;
      tempRoot = mkdtempSync(join(tmpdir(), 'idx-trade-cloudflare-candidate-'));
      const wranglerEntrypoint = resolve(configDir, 'node_modules/wrangler/bin/wrangler.js');
      execFileSync(process.execPath, [
        wranglerEntrypoint, 'deploy', '--dry-run', '--outdir', tempRoot, '--config', configPath,
      ], { cwd: configDir, stdio: 'inherit' });
      bundlePath = findBundle(tempRoot);
    }
    const bundleBytes = readFileSync(bundlePath);
    const modulesDir = pathArg(args.get('--modules-dir'), configDir);
    const compiledModules = modulesDir
      ? readCompiledModules(modulesDir, bundlePath, mainModule)
      : generated
        ? readCompiledModules(tempRoot, bundlePath, mainModule)
        : [{ name: mainModule, content_type: 'application/javascript+module', bytes: bundleBytes }];
    const result = buildCandidateIdentityManifest({
      gitCommitSha: gitSha(repoRoot),
      profile: args.get('--profile'),
      wranglerVersion: wranglerVersion(configDir),
      entrypoint: config.main,
      bundleBytes,
      compiledModules,
      mainModule,
      configBytes: configRaw,
      config,
    });
    const manifestOut = pathArg(args.get('--manifest-out'), process.cwd());
    if (manifestOut) writeFileSync(manifestOut, `${canonicalJson(result.manifest)}\n`, 'utf8');
    console.log(JSON.stringify({
      status: 'CANDIDATE_MANIFEST_GENERATED',
      profile: result.manifest.profile,
      generated_by_wrangler_dry_run: generated,
      bundle_path: bundlePath,
      manifest_path: manifestOut,
      manifest_sha256: result.manifestSha256,
      manifest: result.manifest,
    }, null, 2));
  } finally {
    if (generated && tempRoot) rmSync(tempRoot, { recursive: true, force: true });
  }
}
