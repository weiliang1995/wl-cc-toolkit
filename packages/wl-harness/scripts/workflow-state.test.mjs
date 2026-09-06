import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {
  STAGES,
  readWorkflowState,
  slugify,
  workflowStatePath,
  writeWorkflowState,
} from './workflow-state.mjs';

function makeTempProject() {
  return mkdtempSync(path.join(tmpdir(), 'wl-harness-'));
}

function withTempProject(fn) {
  const dir = makeTempProject();
  try {
    fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('readWorkflowState returns null when the file does not exist', () => {
  withTempProject((dir) => {
    assert.equal(readWorkflowState(dir), null);
  });
});

test('write then read round-trips slug, stage and body', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, {
      slug: 'personal-site',
      stage: 'intake',
      body: '# personal-site\n',
    });
    const state = readWorkflowState(dir);
    assert.equal(state.slug, 'personal-site');
    assert.equal(state.stage, 'intake');
    assert.equal(state.body, '# personal-site\n');
  });
});

test('writeWorkflowState creates the .claude directory when it is missing', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'intake' });
    assert.ok(existsSync(workflowStatePath(dir)));
  });
});

test('a second write advances the stage in place', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'intake' });
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'plan' });
    assert.equal(readWorkflowState(dir).stage, 'plan');
  });
});

test('writeWorkflowState refuses a missing slug', () => {
  withTempProject((dir) => {
    assert.throws(() => writeWorkflowState(dir, { stage: 'intake' }), /slug/);
  });
});

test('writeWorkflowState refuses a missing stage', () => {
  withTempProject((dir) => {
    assert.throws(() => writeWorkflowState(dir, { slug: 'personal-site' }), /stage/);
  });
});

test('slugify lowercases, trims and hyphenates', () => {
  assert.equal(slugify('  My Personal Site!! '), 'my-personal-site');
});

test('slugify returns an empty string for non-ASCII input (pinned, not fixed)', () => {
  // slugify only strips to [a-z0-9]; a fully non-ASCII description collapses
  // to nothing. There is no transliteration dependency here (zero external
  // deps is a hard constraint), so init-project's step 1 must detect this
  // empty result itself and ask the author for an ASCII slug rather than
  // calling writeWorkflowState with one.
  assert.equal(slugify('我的个人网站'), '');
});

test('writeWorkflowState preserves the existing body when body is omitted on update', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'intake', body: '# notes\n' });
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'plan' });
    const state = readWorkflowState(dir);
    assert.equal(state.stage, 'plan');
    assert.equal(state.body, '# notes\n');
  });
});

test('writeWorkflowState defaults to an empty body when creating a new file', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'intake' });
    const state = readWorkflowState(dir);
    assert.equal(state.body, '');
  });
});

test('STAGES lists the eight spine stages in order', () => {
  assert.deepEqual(STAGES, [
    'intake',
    'context-load',
    'design',
    'plan',
    'implement',
    'verify',
    'handoff',
    'ship',
  ]);
});
