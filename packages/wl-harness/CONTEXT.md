# wl-harness

An application-level harness on top of Claude Code that turns the author's stack
preferences and delivery workflow into enforced constraints. This glossary covers
the terms whose meaning was decided rather than inherited.

## Language

**Harness**:
An application-level layer on top of Claude Code that turns the author's stack
preferences and delivery workflow into enforced constraints.
_Avoid_: framework, wrapper, agent

**Layer**:
One of the six concerns the harness is described in terms of. A conceptual
grouping used to reason about responsibility, never a build order.
_Avoid_: tier, module, phase

**Stage**:
One position on the canonical spine every work item passes through, from Intake
to Ship. Stages are shared vocabulary across all commands; a command runs a
subset of them.
_Avoid_: phase, step, tier

**Step**:
One unit of work inside a stage, declared in a plan with its own acceptance and
artifacts. A step is resumable; a stage is not.
_Avoid_: task, item, action

**Gate**:
A constraint that rejects a violation outright. A gate answers "is this
allowed?" and its failure means something is wrong.
_Avoid_: check, guard, rule

**Acceptance**:
A judgement of whether work is finished. It answers "is this done?" and its
failure means work remains, not that a violation occurred. Distinct from a
[[Gate]].
_Avoid_: validation, verification, criteria

**Red line**:
A gate that constrains the agent itself, sealed against modification by the
agent. The subset of gates the overlay may not relax.
_Avoid_: rule, policy, constraint

**Profile**:
The data description of one technology stack: its layout, checks, bans and
verification commands. Profiles are the only place stack knowledge lives.
_Avoid_: preset, template, stack config

**Overlay**:
A project's declaration in `harness.json`, which selects profiles and may narrow
their defaults. An overlay may tighten a profile, never relax it.
_Avoid_: config, override, settings

**Workstate**:
The record of one work item as it moves through `processing → testing →
shipped`. One file per item; the directory it sits in *is* its state.
_Avoid_: task file, ticket, status

**Ship**:
The act of archiving an accepted work item: confirming the code conforms to its
spec and moving the workstate to `shipped`. Ship never touches code.
_Avoid_: release, deploy, publish, merge

**Slug**:
The stable identifier for one work item, shared by its workstate file, its
snapshots and its logs.
_Avoid_: id, name, ticket number
