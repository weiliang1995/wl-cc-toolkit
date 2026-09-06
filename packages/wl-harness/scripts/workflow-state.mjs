// L2 + L4: the single file-state mechanism for S0.
// Nothing here depends on shell variables or in-process state, so a session
// can be compacted or restarted and still resume from the file.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const DELIM = '---';

// Inert documentation of the spine's order. Deliberately not enforced:
// S0 ships no validator (spec 15, 16 D-2).
export const STAGES = [
  'intake',
  'context-load',
  'design',
  'plan',
  'implement',
  'verify',
  'handoff',
  'ship',
];

export function workflowStatePath(projectDir) {
  return path.join(projectDir, '.claude', 'workflow-state.md');
}

export function slugify(text) {
  return String(text)
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Handles only flat `key: value` string pairs. Sufficient for S0's two
// fields; swap in a real YAML parser if the frontmatter ever grows lists.
export function parseFrontmatter(raw) {
  const lines = raw.split(/\r?\n/);
  if (lines[0] !== DELIM) {
    throw new Error('workflow-state.md is missing its opening frontmatter delimiter');
  }
  const fields = {};
  let i = 1;
  for (; i < lines.length; i++) {
    if (lines[i] === DELIM) break;
    const sep = lines[i].indexOf(':');
    if (sep === -1) continue;
    fields[lines[i].slice(0, sep).trim()] = lines[i].slice(sep + 1).trim();
  }
  const body = lines.slice(i + 1).join('\n').replace(/^\n+/, '');
  return { slug: fields.slug, stage: fields.stage, body };
}

export function stringifyFrontmatter({ slug, stage }, body) {
  return `${DELIM}\nslug: ${slug}\nstage: ${stage}\n${DELIM}\n\n${body}`.replace(/\n+$/, '\n');
}

export function readWorkflowState(projectDir) {
  const filePath = workflowStatePath(projectDir);
  if (!existsSync(filePath)) return null;
  return parseFrontmatter(readFileSync(filePath, 'utf8'));
}

export function writeWorkflowState(projectDir, { slug, stage, body = '' }) {
  if (!slug) throw new Error('writeWorkflowState requires a slug');
  if (!stage) throw new Error('writeWorkflowState requires a stage');
  mkdirSync(path.join(projectDir, '.claude'), { recursive: true });
  writeFileSync(workflowStatePath(projectDir), stringifyFrontmatter({ slug, stage }, body), 'utf8');
}
