# Build breadth-first as a walking skeleton, not layer by layer

The six-layer architecture describes `wl-harness` by concern, and it is tempting
to read that list as a build order — contracts first, since everything declares
against them, then orchestration, then gates, and so on. We are not building it
that way.

## Decision

Build breadth-first: cut the thinnest possible hole through all six layers and
run one real work item end to end, then deepen each layer against what that run
taught us. The six-layer structure is a **conceptual map of responsibility, not
a schedule**.

## Considered options

Depth-first by layer was the original plan, ordered L1 → L3 → L6 → L5 → L4 → L2.
It was rejected for two reasons:

- The contract's open questions — the shape of a `steps` entry, the vocabulary
  an `acceptance` assertion is written in, whether `role` is its own field —
  cannot be answered without having run a command. Settling them first means
  guessing, and the contract is the root: reworking it invalidates everything
  declared against it. This is the same failure the harness already guards
  against by generating `schema.md` from `schema.json` rather than writing both.
- Nothing is usable until the orchestration layer is finished, which is most of
  the way through the order.

## Consequences

- Stack knowledge is allowed to be hardcoded in the first slice, when only one
  profile exists. The profile abstraction is extracted when the second profile
  arrives — forced out by a real second case rather than designed in advance.
- Each layer's own design document, which this umbrella defers to, describes the
  layer's *finished* shape. The slices decide the order those shapes are
  approached in, and the two must not be confused.
