---
kind: answer-key
for: handoff.md section 7 (the four comprehension questions)
grader: any idd-figures CC session (Bobby relays the lsae CC's answers)
verdicts: all four solid -> green-light phase 5. Any red flag -> one targeted
  follow-up question (below) before any code moves. Partial answers are fine
  if the MECHANISM is right; grade understanding, not vocabulary.
---

# Grading key for the lsae handoff questions

## Q1 — the `anatomy` name collision

**Expected:** They rename THEIR module (e.g. `transform_anatomy` /
`hdi_anatomy`); the library keeps `layouts/anatomy.py` because `show_anatomy`
is general-purpose tooling while theirs is one published figure. The deeper
half: their module is a *figure* — a layout (3-row composite) plus its
painters — so after the swap the composite becomes a `panel_grid` spec in
their repo and its drawing pieces remain painters; nothing about it belongs in
the shared library.

**Red flags:** proposing the LIBRARY rename; treating the two modules as the
same kind of thing; planning to keep their whole module intact "but renamed"
(misses that the composite is being rebuilt as engine config).
**Follow-up if flagged:** "What does your anatomy module DO that the library's
does not, and which parts of it survive the rebuild?"

## Q2 — why B3 precedes the save switch

**Expected mechanism, all three links:** (1) their `colorbar_axes` places the
bottom bar below the `BOTTOM` margin, so its ticks/label render at NEGATIVE
figure coordinates — outside the declared canvas; (2) `bbox_inches="tight"`
crops to INK, which accidentally rescues that off-canvas text; (3)
`save_figure` enforces `bbox_inches=None` (the declared figsize IS the
output), so switching first makes the bar text silently vanish. Geometry must
put every bit of ink inside the declared canvas BEFORE the save discipline
changes.

**Red flags:** "it's cosmetic"; planning to pass `bbox_inches="tight"` to
save_figure (it has no such escape by design); fixing by enlarging dpi/figsize
rather than the bar placement.
**Follow-up:** "What exactly does bbox_inches='tight' crop to, and what does
that hide?"

## Q3 — why delete-and-reimplement, not port; three transferred lessons

**Expected rationale (any of these, ideally two):** the kit is
geopandas-specific at load-bearing points (the 1/cos(lat) aspect squeeze, the
`ax.collections[0]` mappable harvest, the 2.507 constant); it carries
undisclosed defects the port would inherit (the colorbar-height dead-band
leak, the missing wspace term, B3); and porting would create a SECOND layout
system beside the engine — one canonical implementation is the house rule.
The library rebuilt the capability natively (bars as grid cells, explicit
aspect, derived geometry).

**Three lessons that DID transfer (any three count):** gap charging against
the MEAN cell (`gap_factor`); explicit gridspec margins (matplotlib's defaults
waste 22.5% width); colorbars never carved via `fraction=`/`shrink` (now grid
cells with footprint = served panels); preview mode with CONSTRUCTED stand-in
mappables so bar layout is identical; height derived from width and extent
aspect, never hand-picked; band reservation as height-dependent bottom (their
own `anatomy_layout`'s correct pattern); constants-read-in-bodies for
%autoreload; the `_preview` filename interlock.

**Red flags:** "we'll port it for now and swap later"; inability to name ANY
concrete lesson (suggests they didn't internalize why their numbers worked);
claiming the kit was simply wrong (it wasn't — its algebra was verified exact;
the issue is specificity + defects + duplication).
**Follow-up:** "Your gap_factor was verified exact. Why is it still deleted?"

## Q4 — where loading/saving goes when a painter never loads

**Expected:** `load_spec_map_frames` / `load_spec_distributions` move to their
render (or analysis) layer — data prep is the CALLER's job; figures receive
prepared frames/GeoDataFrames as arguments. `make_figures` /
`make_map_figures` (mkdir + savefig + print loops) are orchestration and move
to `render/`, calling `io.save_figure`. What remains in `lib/figures/` is only:
painters (take an ax, draw, return it) and figure-spec builders that accept
prepared data. Bonus points: noticing `write_aid_explorer` (HTML writer) is
the same violation, and that the module-level `constants` import (output-tree
knowledge inside figures/) goes with the loaders.

**Red flags:** moving loaders INTO idd-figures; leaving any savefig/mkdir in
`lib/figures/`; "the convention allows hybrids" (their letter's §7.5 claim —
our written convention says the opposite, and our one true hybrid was split
for exactly this reason).
**Follow-up:** "After the move, what arguments does the rebuilt map figure
function take, and who computed them?"

## Also verify in their response (not questions, but gate items)

- They acknowledge the two prerequisites AS ordered steps (commit the
  untracked layer FIRST; B3 before save switch).
- They plan per-render-group commits with before/after renders as acceptance
  fixtures (their own current outputs are the reference).
- Nothing in their plan touches idd-figures itself — library gaps come back
  as requests (inbox), not PRs bundled with the migration.
