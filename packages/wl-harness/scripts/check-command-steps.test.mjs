import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const commandsDir = path.join(here, '..', 'commands');

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

const commandFiles = readdirSync(commandsDir).filter((f) => f.endsWith('.md'));

test('there is at least one command to check', () => {
  assert.ok(commandFiles.length > 0);
});

for (const file of commandFiles) {
  test(`${file}: frontmatter steps align 1:1 with the numbered body lines`, () => {
    const raw = readFileSync(path.join(commandsDir, file), 'utf8');
    const steps = frontmatterSteps(raw);
    const numbered = numberedBodyLines(raw);
    assert.ok(steps.length > 0, 'no steps found in frontmatter');
    assert.equal(
      steps.length,
      numbered.length,
      `frontmatter declares ${steps.length} steps but the body has ${numbered.length} numbered lines`,
    );
  });
}
