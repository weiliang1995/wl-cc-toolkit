// L6: S0's single red line.
// Spec 6.5 — business code imports UI primitives only from src/components/ui/.
// S0-HARDCODE: the library name and the directory are fixed here. In S2 they
// come from the profile's `forbidden` rules instead.

import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const CODE_FILE = /\.(ts|tsx|js|jsx)$/;
const UI_DIR = /(^|\/)src\/components\/ui\//;
const ANTD_IMPORT = /from\s+['"]antd['"]/;

export function shouldBlockUiImport(filePath, content) {
  const normalised = String(filePath).replace(/\\/g, '/');
  if (!CODE_FILE.test(normalised)) return false;
  if (UI_DIR.test(normalised)) return false;
  return ANTD_IMPORT.test(content);
}

function readStdin() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', () => resolve(''));
  });
}

// Any failure ends in exit 0 with empty stdout: Claude Code reads "no output"
// as "the hook made no decision", so a crash can never wedge the session.
async function main() {
  try {
    const raw = (await readStdin()).replace(/^﻿/, '').trim();
    if (!raw) return;

    const filePath = JSON.parse(raw)?.tool_input?.file_path;
    if (!filePath) return;

    const content = readFileSync(filePath, 'utf8');
    if (!shouldBlockUiImport(filePath, content)) return;

    process.stdout.write(JSON.stringify({
      decision: 'block',
      reason:
        `${filePath} imports "antd" directly. Business code may only import UI ` +
        'primitives from src/components/ui/ — wrap the component there and import ' +
        'the wrapper instead.',
    }));
  } catch {
    // Deliberately silent.
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  main().then(() => process.exit(0), () => process.exit(0));
}
