import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { shouldBlockUiImport } from './check-ui-imports.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(here, 'check-ui-imports.mjs');

function runHook(filePath) {
  return execFileSync(process.execPath, [SCRIPT], {
    input: JSON.stringify({ tool_name: 'Write', tool_input: { file_path: filePath } }),
    encoding: 'utf8',
  });
}

function withTempFile(name, contents, fn) {
  const dir = mkdtempSync(path.join(tmpdir(), 'wl-harness-hook-'));
  try {
    const filePath = path.join(dir, name);
    writeFileSync(filePath, contents, 'utf8');
    fn(filePath);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('blocks a direct antd import outside components/ui', () => {
  assert.equal(
    shouldBlockUiImport('src/app/page.tsx', 'import { Button } from "antd";'),
    true,
  );
});

test('allows a direct antd import inside src/components/ui', () => {
  assert.equal(
    shouldBlockUiImport('src/components/ui/Button.tsx', 'import { Button } from "antd";'),
    false,
  );
});

test('allows the same path written with backslashes (Windows)', () => {
  assert.equal(
    shouldBlockUiImport('src\\components\\ui\\Button.tsx', "import { Button } from 'antd';"),
    false,
  );
});

test('ignores code with no antd import', () => {
  assert.equal(
    shouldBlockUiImport('src/app/page.tsx', 'import { Fragment } from "react";'),
    false,
  );
});

test('ignores non-code files', () => {
  assert.equal(
    shouldBlockUiImport('src/styles/globals.less', '.antd-override { color: red; }'),
    false,
  );
});

test('as a hook: emits a block decision for an offending file', () => {
  withTempFile('page.tsx', 'import { Button } from "antd";\n', (filePath) => {
    const result = JSON.parse(runHook(filePath));
    assert.equal(result.decision, 'block');
    assert.match(result.reason, /components\/ui/);
  });
});

test('as a hook: emits nothing for a clean file', () => {
  withTempFile('page.tsx', 'import { Fragment } from "react";\n', (filePath) => {
    assert.equal(runHook(filePath), '');
  });
});

test('as a hook: emits nothing when the file no longer exists', () => {
  assert.equal(runHook(path.join(tmpdir(), 'wl-harness-does-not-exist.tsx')), '');
});
