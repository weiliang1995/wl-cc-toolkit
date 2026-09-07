import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.join(here, '..');
const repoRoot = path.join(pluginRoot, '..', '..');

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'));
}

test('plugin.json declares name, version and description', () => {
  const manifest = readJson(path.join(pluginRoot, '.claude-plugin', 'plugin.json'));
  assert.equal(manifest.name, 'wl-harness');
  assert.match(manifest.version, /^\d+\.\d+\.\d+$/);
  assert.ok(manifest.description.length > 0);
});

test('package.json is ESM and has no dependencies', () => {
  const pkg = readJson(path.join(pluginRoot, 'package.json'));
  assert.equal(pkg.type, 'module');
  assert.equal(pkg.dependencies, undefined);
  assert.equal(pkg.devDependencies, undefined);
});

test('the marketplace lists wl-harness, pointing at this package', () => {
  const marketplace = readJson(path.join(repoRoot, '.claude-plugin', 'marketplace.json'));
  const entry = marketplace.plugins.find((p) => p.name === 'wl-harness');
  assert.ok(entry, 'wl-harness is missing from marketplace.json');
  assert.equal(entry.source, './packages/wl-harness');
});
