# Design template

The dimensions stage 3 must reach before a spec is finished. Read the section
matching each declared profile `kind`; skip entries whose tier annotation
excludes the project's complexity.

**This is domain knowledge, not stack knowledge.** "A view needs loading, empty
and error states" is true of React, Vue and Svelte alike, so it lives here rather
than in a profile — a profile would make every new stack recopy it (§7).

## How to use it

1. Fill every dimension you can from what the author already gave you — the
   command's argument, a supplied document, the repository itself.
2. Put the rest to the author as one batch, each with your recommendation and
   the alternatives you passed over. A dimension where you picked between
   candidates is a decision and must be surfaced as one; a dimension fixed by
   the stack block or stated outright by the author is written as fact and not
   asked about.
3. Rewrite the spec from the answers.
4. **Record every skip.** Write the default into the spec — "Pagination: not
   specified, defaulting to 10 per page". A defaulted decision and one nobody
   considered look identical in the finished code and are not the same thing.

Keep the first version short. A template long enough to cause fatigue ends in
rubber-stamping, which is worse than not asking: it manufactures the appearance
of alignment.

## Every kind

### Acceptance traceable to purpose — must-answer

At least one acceptance criterion has to trace back to a word in the spec's
Purpose. The harness's own red lines do not count toward this, and neither do
checks generic to the stack.

*Why:* left alone, acceptance criteria default to whatever the harness can
already check — the set that needed no thought. The first `init-project` run
produced "`tsc --noEmit` passes", "every route renders", and "no `antd` outside
`src/components/ui/`" against a Purpose of *presenting who the author is, what
they have built, and how to reach them*. Four blank pages satisfy all three.

### Content ownership — must-answer, no default

Who supplies the real copy: the author, a CMS, or deliberate placeholder?

*Why:* an agent can propose an information architecture and cannot possibly know
a biography, a project list or a contact address. The first run was asked for
neither and invented all three. Where the answer is "the author", say so in the
spec and mark the placeholders, rather than shipping fiction that has to be found
and replaced later.

**There is no default here. If it is unanswered, stop and ask.**

## frontend

### Navigation model — must-answer

Separate routes, single-page anchors, or a tab view driven by
`history.replaceState`.

*Why:* it decides the route table, whether views are deep-linkable, and whether
each view can carry its own metadata. For a small static site the three are
genuinely different products, not implementation details.

*Default if unstated:* separate routes — which is what the first run chose
silently, without the choice ever becoming visible to the author.

### Per-page metadata and open-graph — must-answer

Does each view need its own title, description and preview image, or is one set
at the root enough?

*Why:* the crawlers behind link previews — LinkedIn, X, WeChat, Slack — do not
execute JavaScript. A site without server-rendered tags previews blank wherever
it is shared, which for anything meant to be shared is a functional defect
rather than a polish item.

*Default if unstated:* root-level metadata only.
