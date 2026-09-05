# The overlay may tighten a profile, never relax it

`wl-harness` splits stack knowledge into profiles (defaults, shipped with the
harness) and a per-project overlay in `.claude/harness.json`. The obvious design
is a symmetric override layer, where the overlay replaces any profile field. We
rejected that: profiles carry the `forbidden` rules that constrain the agent, and
the overlay is a committed file the agent is able to edit, so a symmetric
override would let the agent switch off its own red lines by writing
`"forbidden": []`.

## Decision

Two rules, both mechanically checked:

1. **Sealed fields.** Each profile field is marked `overridable: true | false`.
   `forbidden`, `layout` and `migration_policy` are sealed; `db`, `complexity`
   and `deploy` are overridable. `harness-check.mjs` rejects an overlay that
   touches a sealed field.
2. **Tighten-only merge.** Where an overlay does apply to an array field, the
   merge is a union, never a replacement — an overlay can add a ban, not remove
   one.

## Consequences

- Relaxing a red line requires editing the profile itself, which ships with the
  harness rather than with the project. That is deliberate friction: it makes
  the change visible and reviewable instead of a one-line edit in a project file.
- The same principle settles the general question "which layer owns this field":
  a profile is the source of defaults, an overlay is a narrowing. Any future
  field can be placed by asking whether relaxing it should be a project's
  decision.
