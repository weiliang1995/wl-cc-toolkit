import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const commandsDir = path.join(here, '..', 'commands');

// core.autocrlf is true in this repo, so any checkout on Windows — a fresh clone,
// a branch switch, a merge — materialises these files with CRLF, while git still
// reports them unchanged. The patterns below anchor on \n, so normalise on read:
// without this the only mechanical gate S0 ships fails on every Windows clone.
function readCommand(file) {
  return readFileSync(path.join(commandsDir, file), 'utf8').replace(/\r\n/g, '\n');
}

// Spec section 5: the frontmatter `steps` array must match the body's ^N.
// lines one-for-one. That alignment is what makes a run resumable.
function frontmatterSteps(raw) {
  const block = raw.match(/^steps:\n((?:\s*-\s+.+\n)+)/m);
  if (!block) return [];
  return block[1]
    .split('\n')
    .filter((line) => line.trim().startsWith('-'))
    .map((line) => line.trim().replace(/^-\s*/, ''));
}

function numberedBodyLines(raw) {
  const body = raw.split(/^---$/m).slice(2).join('---');
  return body.match(/^\d+\.\s/gm) ?? [];
}

// Extract the bolded stage name that opens each numbered body line, e.g.
// "1. **Intake** — Derive the slug..." -> "Intake". Falls back to the raw
// line when a numbered line is not bolded, so a missing bold still shows up
// as a mismatch rather than silently vanishing from the comparison.
function numberedBodyStageNames(raw) {
  const body = raw.split(/^---$/m).slice(2).join('---');
  const lines = body.match(/^\d+\.\s+.*/gm) ?? [];
  return lines.map((line) => {
    const match = line.match(/^\d+\.\s+\*\*(.+?)\*\*/);
    return match ? match[1] : line;
  });
}

// A space and a hyphen are the same separator for this purpose
// ("context-load" in frontmatter vs "Context load" in prose), so normalize
// both before comparing, case-insensitively.
function normalizeStageName(name) {
  return name.trim().toLowerCase().replace(/[\s-]+/g, '-');
}

const commandFiles = readdirSync(commandsDir).filter((f) => f.endsWith('.md'));

test('there is at least one command to check', () => {
  assert.ok(commandFiles.length > 0);
});

for (const file of commandFiles) {
  test(`${file}: frontmatter steps align 1:1 with the numbered body lines`, () => {
    const raw = readCommand(file);
    const steps = frontmatterSteps(raw);
    const numbered = numberedBodyLines(raw);
    assert.ok(steps.length > 0, 'no steps found in frontmatter');
    assert.equal(
      steps.length,
      numbered.length,
      `frontmatter declares ${steps.length} steps but the body has ${numbered.length} numbered lines`,
    );
  });

  test(`${file}: frontmatter steps match the body's stage names, in order`, () => {
    const raw = readCommand(file);
    const steps = frontmatterSteps(raw);
    const stageNames = numberedBodyStageNames(raw);
    assert.deepEqual(
      stageNames.map(normalizeStageName),
      steps.map(normalizeStageName),
      `frontmatter steps [${steps.join(', ')}] do not match body stage names [${stageNames.join(', ')}] in order`,
    );
  });
}
