# Beeswarm extraction feasibility record

Started 2026-09-02. Working file for the five-step investigation requested in
chat; the chat carries one-line checkpoints, this file carries the findings.
Sections fill in as each step lands. "Measured" and "estimated" are labelled.

## Scope (from Bobby)

1. D-normalized boundary refactor (decided). Core works in an isotropic,
   dimensionless space with collision diameter 1; boundary takes anchors plus
   the diameter in category-units and value-units; optimizer searches D.
2. Collision backend seam: circle (closed form, existing) and convex polygon
   (vertices from the notebook's `get_marker_geometry`). Propose the cut first.
3. Shapely question: numpy segment distance vs shapely oracle; report which
   world we are in.
4. C99 port of the core before any packaging; circle first, polygon only if
   step 3 landed on numpy; wire to Python; measure phi and spine-drop+phi.
5. Sketch the package. Do not build it.

## Environment facts (measured 2026-09-02)

- gcc 9.4.0 at /usr/bin/gcc. shapely 2.1.2 present in .venv (maps extra).
  cffi absent, so C wiring uses stdlib ctypes. `*.so` is gitignored.
- Existing tests import from `idd_figures.idd_beeswarm`: SCATTER_LW, TOL_PX,
  _middle_out_order, _processing_order, _spine_bin_order, idd_beeswarm,
  position_all_points. Layout tests run at fixed s=70 on an 8x2.8 in figure,
  orient="h", one_sided=True; min pair distance asserted >= visual D - 1e-6 px.

## Step 1: D-normalized boundary (done 2026-09-02, uncommitted)

**What changed.** New module `src/idd_figures/beeswarm_core.py` (742 lines):
the engines moved over verbatim and run at D = 1 on `a = cat/dx`, `b = val/dy`;
`layout(cat, val, dx, dy, ...)` divides in / multiplies out and returns
(cat_new, val_new, extent); `find_optimal_size(cat, val, margin, dx_unit,
dy_unit, d_min, d_max, ...)` bisects a physical diameter `d` in whatever unit
the wrapper uses and calls `layout(cat, val, d*dx_unit, d*dy_unit)`. No
matplotlib, no pandas in the core. `idd_beeswarm.py` is now the matplotlib
unit supplier (290 lines): `visual_diameter_px(s, dpi, gap)` and its inverse
`marker_size_from_diameter_px`, `_px_per_unit(ax, orient)`, and the three
historical entry points with unchanged signatures. `TOL_PX` (1e-6 px) became
`TOL = 1e-9` in D units. The optimizer's failure print became a
RuntimeWarning; the `find_optimal_s.history` function attribute is gone.
Test imports repointed; `tests/test_beeswarm_core.py` added (unit invariance,
overlap in normalized space, sign flip of dx, tie-break, optimizer, warnings).

**Measured: tests.** 55 passed (20 pre-existing + 35 new), 3.2 s.

**Measured: parity vs the pre-refactor module (git HEAD, run in memory), 72
configs = 3 figures x 2 sidedness x 12 modes, same s.**
- one_sided=True: 35/36 configs agree to <= 5e-8 data units (the residual is
  the ellipse bisection's tolerance in a different unit); one config
  (middle-out, phi=3, n=60) differs by 7e-3 in one dot, extent identical.
- one_sided=False: 25/36 configs differ, up to 0.85 data units, extents
  identical to 1e-16 in most (whole stacks mirrored), extents off by up to
  3.5e-2 in three (a flip cascaded into different later choices).
- Cause: two-sided layouts contain exact mirror ties (a dot can go left or
  right with equal |shift|). The old code resolved them by whichever
  candidate rounded smaller, so the result depended on the unit the anchors
  arrived in. Confirmed by observing that the first parity run (before any
  tie rule) mirrored differently from pixel-space on symmetric stacks.
- Fix installed: `_pick(values, *prefer)` selects the min with ties within
  TOL broken toward the positive offset side (then higher value), at the
  three selection sites (`_layout_swarm`, `_drop_at_value`, `_phi_best`).
  New code is unit-invariant (tested: rescaling anchors and diameters
  together rescales the layout exactly). Consequence: two-sided layouts are
  NOT bit-identical to 2026-08-31 output; they are the mirror-consistent
  version. This same rule is what a C implementation will need to match.

**Measured: optimizer, bisect D vs bisect s.** spine-drop n=60: s 24.568 vs
24.563, 15 vs 14 iterations. ascending n=120: identical s (61.135), 19 vs 13
iterations. middle-out+phi=3 n=120: old 143.5 in 28 iterations, new 135.1
after hitting the 50-iteration cap (extent 0.493 vs 0.478, both within
margin). The exit criteria (error < tol, or five successive improvements
within tol_seq) are heuristics on a discontinuous extent(D); which path they
take depends on the bisection variable. Not changed; flagged.

**Observations, not acted on.**
- The swarm engines' `None` ("no valid position") return is effectively
  unreachable: the outermost tangent candidate is always clear of every
  neighbour, so validity is decided by extent > margin alone. Grids never
  return None either. The optimizer's invalid branch is dead in practice.
- The wrapper reads pixels-per-unit at the origin, i.e. assumes an affine
  data transform. Log-scale value axes would need the wrapper to pass
  transformed coordinates. The old code had the same assumption in its
  shift back-conversion.
- Anchors for a category share one float, so a category's dots all sit at
  exactly the same `a`; nothing in the normalization disturbs grouping.

**Effort (measured).** About 90 minutes including the parity harness and
tests. The refactor itself was mechanical; the tie-break finding was the
only surprise.

## Step 2: collision seam (done 2026-09-02, uncommitted)

**Cut.** One contract, `shape.forbidden(dval) -> (idx, lo, hi)`: for each
placed neighbour at value separation `dval`, the relative offset interval(s)
inside which the moving mark overlaps it. New module
`src/idd_figures/beeswarm_shapes.py` (270 lines). The core's per-point step
is one consumer, `_min_shift_position` in `beeswarm_core.py`: anchor stays if
strictly inside no interval; else candidates are all endpoints, an endpoint
is valid if strictly inside no interval, min |shift| wins with `_pick`.
Used by `_layout_swarm` and `_drop_at_value` (hence spine-drop). Spine
thresholds use `shape.stack_height`; the near filter uses
`shape.half_height`; extent uses `shape.half_width`.

- Circle: tangent pair +-sqrt(1 - dval^2). Same algebra as before; all 55
  Step 1 tests still pass through the seam.
- Convex polygon: K = Q (+) (-P) as the hull of pairwise vertex differences,
  built once; forbidden interval = horizontal cut of K at dval
  (`_silhouette`, vectorized over edges and heights). Closed form.
- Non-convex: `mode="hull"` (default) packs the hull, one interval;
  `mode="decompose"` fans from the centroid and merges adjacent pieces while
  convex (a 5-star -> 5 kites), one interval per piece pair (25 for the
  star). Exact under the same consumer. Requires the mark to be star-shaped
  about its centroid; otherwise raises.
- Wrapper: `marker_vertices_px(marker, s, dpi, linewidth)` productionizes the
  notebook's `get_marker_geometry` polygon branch (scatter's scaling, path
  flattened with `to_polygons`, stroke as a mitered offset by LW/2);
  `marker_shape(...)` puts it in D units (D = the stroked circle's collision
  diameter at that s, so 'o' is the unit disk); `marker=`, `shape_mode=`
  threaded through the three entry points. The optimizer rebuilds the shape
  per size because the stroke is not proportional to s (`shape` may be a
  callable of d).

**Measured: matplotlib markers.** Every standard filled marker flattens to
one polygon. Convex: s D d ^ v < > p h H 8 (and o, 24-gon; we use the disk).
Concave: `*` (10 vertices), `P` (12), `X` (12). No interior: `+ x`
(raise). So "hull the star by default, decompose if asked" is the stated
behaviour for `*`, `P`, `X`.

**Measured: tests.** 110 pass (55 + 55 new), 4.4 s. shapely is a test-only
oracle: random convex marks at random heights (interval endpoints touch,
just inside overlaps, just outside does not), the star in both modes against
real polygon overlap on an (a, dval) grid, full layouts of squares,
triangles, hexagons and stars checked pairwise, and the wrapper's `^`, `s`,
`D`, `*` layouts checked pairwise in pixel space.

**Bugs the oracle found.** (1) A cut exactly along K's top or bottom edge was
reported as a full-width forbidden interval; that is edge-to-edge touching.
Fixed by cutting only strictly inside K's vertical extent. (2) For
`orient="h"` the outline entered the core in plot (x, y) order while the
core's first axis is the category axis, so the `^` triangle was packed
rotated 90 degrees (0.77 px^2 overlap). Fixed by transposing in
`marker_shape`; square and diamond had hidden it.

**Not done, by decision (Bobby, 2026-09-02): the visual hull-vs-decompose
star comparison.** Shapes are not a must-have; the C question is.
Decompose exists, is tested, and is opt-in; whether it is visibly better
than hull at real sizes is unmeasured.

**Load-bearing limitation (stated).** Exact for convex pieces. Non-convex
is exact only up to the decomposition, approximate under hull. The stroke
is a mitered offset (exact on edges, mitered corners). Grids and phi are
circle-only and raise NotImplementedError for other shapes.

**phi with polygons, estimate only.** Would need the metric-closest point on
each K's boundary under the sqrt(phi) scaling (per-edge projections) plus
K-K boundary intersections (segment pairs) plus constraint-line hits, and a
domination bound that is no longer a clean sqrt(c0/phi) window because K is
not a disk. Roughly the size of `_phi_best` again with more cases. Left
unbuilt; the seam does not block it.

**Effort (measured).** About 45 minutes: ~30 for seam + convex + wrapper +
oracle tests, ~15 for the non-convex tier. Polygon path is interval
arithmetic and would port to C like the circle path; not being ported
(not critical).

## Step 3: shapely question (resolved by the Step 2 cut)

No runtime min-distance function exists. Placement uses only: hull of small
point sets, Minkowski sum via that hull, horizontal cuts of a convex polygon.
shapely appears only in tests (`pytest.importorskip`). We are in the numpy
world; the polygon path is C-portable. The degenerate cases Bobby listed
(parallel edges, coincident vertices, one polygon inside another,
vertex-touching) are covered by construction or by test: duplicates and
collinear points are dropped by the hull; vertex touches and edge-along-edge
cuts are excluded from the forbidden set (touching is allowed); containment
is a cut with lo < a < hi like any other overlap.

## Step 4: C port (stopped by decision 2026-09-02 after circle greedy + phi; spine-drop and polygon not ported)

**Built.** `src/idd_figures/_c/beeswarm_core.c` (~300 lines, C99, libm only):
`bs_layout_swarm` (greedy value-exact, via the forbidden-interval consumer),
`bs_layout_phi` (phi-penalized, all candidate types, bounds, one-sided), and
two per-point exports for tests (`bs_phi_best`, `bs_ellipse_closest`).
`src/idd_figures/beeswarm_c.py` is a ctypes bridge: `build()` runs one gcc
command producing `_c/libbeeswarm_core.so` beside the source (gitignored by
the existing `*.so` rule), `lib()` loads it on first use and rebuilds when
the .c is newer. Compile + load measured at 0.57 s. Tests:
`tests/test_beeswarm_c.py` (parity across orders, sidedness, phi, bounds;
skipped when gcc is absent).

**What ported cleanly (measured).** The greedy swarm: bit-exact parity with
Python (max diff 0.0 over 8 configs), first try. The phi engine: ~150 lines
of C mirroring `_phi_best`; parity to 5e-9 after one shared fix (below).
The tie-break rule from Step 1 is what made bit-exact parity possible; the
C `pick()` is the same three-key rule.

**What fought (measured).** One divergence, and it was a Python weakness the
port exposed rather than a transcription error: `_ellipse_closest` bisected
the Lagrange multiplier t, whose root for an on-axis query (a placed dot
exactly on the category line, the common case for a category's first dot)
sits ~1e-9 from a pole. Both implementations lost ~5 digits to cancellation
in t + alpha^2 and disagreed at 3e-5 in the projected point, which changed
which candidate won and cascaded to 5.85 D-unit layout differences at phi=3.
Fixed identically in both: solve in s = distance from the pole (one of the
two shifts is exactly zero, so no cancellation) and polish with three Newton
steps. The on-axis case now lands on the ellipse to 1e-15 and the two
implementations agree to 0.0 there. Side effect: the Python phi engine is
more accurate than before (its projections had been off by up to ~1e-4 D,
occasionally making a tangent candidate look invalid and costing a better
position).

**Speed (measured, one layout, ascending, one-sided, 3 categories).**

| n | path | python | C | speedup |
|---|---|---|---|---|
| 300 | swarm | 0.0089 s | 0.00049 s | 18x |
| 1000 | swarm | 0.034 s | 0.0038 s | 9x |
| 3000 | swarm | 0.131 s | 0.024 s | 5x |
| 300 | phi=1 | 0.233 s | 0.024 s | 10x |
| 1000 | phi=1 | 3.25 s | 0.44 s | 7x |
| 3000 | phi=1 | not run | 7.4 s | |

Honest reading: 5 to 18x, not the ~100x I estimated a priori. The Python is
already vectorized over the O(m^2) inner work (m = neighbours in the window),
so C removes per-point interpreter overhead but the same arithmetic remains.
Both are O(n * k) in the neighbour scan (k = placed so far) and O(m^2) per
point in phi's pair candidates; the speedup shrinks as n grows because the
arithmetic dominates. A bigger win in either language would be algorithmic
(sort by value and binary-search the window; prune pair candidates by the
cost bound), not the language. phi at n=1000 is 0.44 s per layout in C, so
a 30-iteration optimizer is ~13 s: usable, not instant.

**Wiring friction (measured).** None on this machine: gcc present, ctypes in
stdlib, numpy's `ndpointer` for the arrays, one build command. The `.so`
lives in the source tree, which is fine for a probe and wrong for a package
(Step 5: proper extension + wheels).

**Not yet done.** `_spine_drop_layout` in C (the expected worst offender:
dynamic order, per-bin queues, lazy re-evaluation cache; in C this is
arrays indexed by point id plus a stable index sort, est. 150-200 lines and
1 to 1.5 hours including parity). Polygon path in C (interval arithmetic
like the circle path; est. 150 lines; not critical per Bobby). Timing of
spine-drop+phi (Python baseline 33 s at n=1000 in the earlier harness).

**Is C a non-starter?** No, on the evidence so far. The kernel is loops over
doubles, the wiring is one gcc call, and parity was reached in two rounds.
The open question is whether 5-18x justifies a compiled dependency in the
package; see Step 5.

**Conclusions (Bobby, 2026-09-02).**

- *Why 5-18x and not 100x.* The Python inner loop was already numpy, i.e.
  already compiled C for the O(m^2) arithmetic. The port removed interpreter
  and dispatch overhead around the array ops, not the arithmetic, which is
  why the ratio shrinks as n grows. Corollary: the next real speedup is
  algorithmic and language-agnostic, not compiled.
- *Where the per-plot cost is.* Cost ~ (optimizer bisection steps, 15-50) x
  (one-layout cost, the table above). The C work attacked the second
  factor. The first, the outer `find_optimal_s` search, is the original
  naive bisection with a fixed cap and the s_min=100 floor flagged in Step 1,
  and has never been touched. It is the bigger lever, pure Python, and it
  stacks multiplicatively with C. It is also the only true optimization in
  the stack: root-finding on the extent of an order-dependent greedy layout,
  with no analytic form, so no coordinate warp collapses it. Everything else
  is exact warps or closed-form-plus-bounded-solve geometry.
- *Roadmap for future performance work, in priority order, NOT built now:*
  (1) smarter outer search: secant or Brent instead of bisection, a cheap
  density-based initial bracket, fewer evaluations; (2) spatial indexing in
  placement to cut the O(m^2) and O(k) neighbour work at large n; (3) C, the
  smallest structural lever.
- *The win.* The port surfaced and fixed a real Python bug (Lagrange
  multiplier pole precision loss changing which phi candidate won). Python
  phi is more accurate than before, independent of whether C ships.
- *Per-plot numbers that drove the decision (derived, steps x table):*
  n=1000, phi=1: ~50-160 s Python vs ~7-22 s C per plot. That is the
  difference between a usable phi and one nobody waits for. Stop porting
  here: spine-drop in C would not change the conclusions.

**Decision (Bobby): C ships as an optional accelerator with a guaranteed
pure-Python fallback, never as a requirement.** pip install works everywhere
with zero toolchain; the kernel is used transparently when present, skipped
when not. Safe because C only changes speed, never results (the parity gate
is what buys that).

## Step 5: package sketch (sketch only, 2026-09-02; nothing built)

### Shape of the package

- **Core** (`beeswarm_core`, `beeswarm_shapes`): pure Python, **numpy only**.
  Confirmed: nothing else is imported today. Public surface: `layout`,
  `find_optimal_size`, `CircleShape`/`PolygonShape`, `convex_hull`,
  `offset_polygon`. Arrays in, arrays out.
- **matplotlib wrapper** as an optional extra `[mpl]`: `idd_beeswarm`,
  `position_all_points`, `find_optimal_s`, `marker_vertices_px`,
  `marker_shape`. The only thing that forces matplotlib is the marker path
  and the axes transform, which is the wrapper's whole job.
- **No pandas.** Today it is used only in the wrapper (DataFrame result,
  column access, `groupby` for colours). Replace with a dict of arrays or a
  small result class and accept any array-likes; keep DataFrame in as a
  convenience if `pandas` happens to be importable. Nothing forces it.
- **No shapely.** Test-only oracle (`pytest.importorskip`). The
  Minkowski-interval cut means production never computes polygon
  min-distance.
- **What the compiled kernel forces:** a build backend that can compile C.
  `uv_build` (this repo's backend) builds pure-Python packages only, so the
  package would move to setuptools (with the extension marked `optional=True`
  so a failed compile still yields a pure-Python install) or scikit-build-core
  / meson-python. This is the one structural consequence of the C decision.
- **Python floor:** 3.10. Nothing in the code needs 3.12.

### Optional-C dispatch (design, per the decision above)

- Try-import the compiled kernel at load; set `_HAVE_C`. The branch lives at
  the Step 1 seam: `layout()` dispatches to `beeswarm_c.layout_swarm` /
  `layout_phi` when available, else `_layout_swarm` / `_layout_phi`. One
  place. Shapes other than the circle, grids, and spine-drop take the Python
  path regardless (not ported).
- `backend="auto" | "c" | "python"` on the public functions, default
  `"auto"`. `"c"` when unavailable raises `RuntimeError` with the reason;
  never a silent fallback. `has_fast_backend()` returns the flag so users
  can see which path they are on and tests can assert parity when both exist.
- Fallback semantics: no wheel and no compiler -> install succeeds on pure
  Python, phi runs slow. Degraded, never broken.
- Parity as a release gate: `tests/test_beeswarm_c.py` (today: swarm
  bit-exact, phi to 1e-7) becomes a required CI job on every wheel platform,
  so the two implementations cannot drift silently. The kernel's contract is
  "same result as Python to 1e-9 D", not "faster".
- The kernel should become a stable-ABI (`Py_LIMITED_API`, abi3) extension
  with ~100 lines of buffer-protocol glue, rather than the ctypes-loaded raw
  `.so` of the probe: one wheel per platform independent of Python version,
  and no `.dylib`/`.dll` naming games.

### Wheel matrix: honest read of the standing cost

- **Setup (estimate, one time):** about one day. setuptools extension with
  `optional=True`, abi3 glue, a cibuildwheel GitHub Actions workflow (~40
  lines), trusted publishing to PyPI. Targets: manylinux x86_64 and
  aarch64, macOS x86_64 and arm64, Windows amd64: five wheels, plus the
  sdist. One CI run of 10-15 minutes per release.
- **Ongoing (estimate):** low in the median, spiky in the tail. Median: a
  cibuildwheel and manylinux image bump roughly yearly, new Python versions
  free under abi3, two to four hours a year. Tail: a wheel that fails to
  import on a platform you do not own (a Windows MSVC quirk, a macOS
  deployment-target change), arriving as issue reports you cannot reproduce
  locally. A 300-line C99 file with no dependencies beyond libm, no threads,
  no I/O, is about the best case for this; the abi3 choice removes the
  largest recurring driver (per-Python rebuilds).
- **Named plainly:** the wheel infrastructure is larger than the kernel it
  ships. It only pays if phi is a headline feature, which is the decision.
- **Sequencing that respects the decision without paying the cost up front:**
  v0.1 pure Python (numpy, optional matplotlib), roughly one day beyond what
  exists now; v0.2 adds the optional C accelerator. Because the fallback
  design makes the accelerator a non-breaking addition, nothing about v0.1
  has to be undone. This de-risks the first publish and delays the wheel
  matrix until someone actually hits phi slowness in the wild.

### API cleanup for a public library (from the Step 1 audit; ~2-3 hours)

Return values instead of `plt.show()` (return the axes, the layout, and the
chosen size); `warnings` instead of prints; single-colour default with
`color_var`/`color_dict` optional; fix the s_min floor and iteration cap
(search D from a density-based bracket, exit on a D tolerance); remove the
dead `verbose_inner` / `verbose_optim_full`; `SCATTER_LW` as a parameter;
`backend` kwarg and `has_fast_backend()`; make `layout` / `find_optimal_size`
the primary documented API with the matplotlib function as the thin wrapper.

### Test-vector harvest (to write, not written)

- The notebook's hand-built known-good stacks
  (`notebooks/idd_beeswarm/point_distance.ipynb` cells 8-13: tangent-circle
  shift constructions with edge-to-edge distance checks) as regression
  fixtures for the circle path in normalized units.
- The degenerate stacked-data probe and the two-category four-colour
  `draw_margin` demo from `notebooks/idd_beeswarm/idd_beeswarm.ipynb`
  (already earmarked for the vignette).
- Circle-via-many-sided-polygon cross-check: `PolygonShape(regular 64-gon)`
  layouts against `CIRCLE` layouts, with the inscribed-polygon tolerance
  (apothem cos(pi/64) ~ 0.9988) stated.
- The Step 1 parity harness (HEAD module in memory) is one-off; the
  invariant tests replace it.

### Shape support status

In production: circle (closed form) and convex polygon via the
Minkowski-silhouette interval, exact. Non-convex: hull (default, approximate,
one interval) or convex decomposition (opt-in, exact up to the
decomposition, k^2 intervals per neighbour, requires star-shaped about the
centroid). Matplotlib: `*`, `P`, `X` are the concave markers; `+`, `x` have
no interior and raise. **The hull-vs-decompose visual test was not run**
(decision: shapes are not a must-have), so whether decompose is visibly
better at real sizes is unmeasured. phi with polygons: unbuilt; documented
above as future work with the candidate types it would need. Grids:
circle-only. None of the polygon path is in C.

### Effort spent on the investigation (measured, wall clock)

Step 1 ~1.5 h (incl. parity harness and tests), Step 2 ~45 min, Step 4
~1.5 h, write-ups ~30 min. About 4.5 h total.

### Honest read: is the public repo more or less worth doing than it looked?

**More worth doing on the technical side than at the start.** The module
was more self-contained than assumed (no repo-internal imports at all); the
core/wrapper split fell out in 90 minutes; the shape seam gave exact convex
polygons for ~270 lines because the closed form exists; the C port is 300
lines, bit-exact, and wired with one command; and the investigation fixed
two real bugs in the in-house tool (unit-dependent mirror ties, the ellipse
pole precision loss) that pay off whether or not anything is published.

**Less worth doing on the audience side than the feature list suggests.**
The visible differentiators are auto-sizing to a margin, phi, the
processing orders, and exact packing of non-circular markers. None of
seaborn's `swarmplot` or R's ggbeeswarm has them, and I know of no package
that packs shapes exactly. But the audience that notices dot size and
value-fidelity trade-offs is the publication-figure audience, which is
small, and seaborn is already installed on their machines. Adoption will be
slow and issue-driven.

**The standing costs are real and now sized:** the wheel matrix (a day up
front, a few hours a year, occasional unreproducible platform reports), the
API cleanup (hours), a vignette (already planned), issue triage (unknown,
proportional to adoption), and the R side (undecided; one to two weeks for a
draw-time geom on the shared core, which the dimensionless boundary was
designed to make possible).

**Net:** worth doing as a clean, tested home for this code and as the
substrate for an R geom later, at the cost of roughly one day for a
pure-Python v0.1 and the wheel matrix only when phi demand justifies it. Not
worth doing as a growth product, and the decision to publish should not
rest on adoption. If the R geom is never built, the dimensionless core and
the optional C kernel still earned their keep by fixing two bugs and making
phi usable in-house.

## Decisions needed from Bobby

(Step 1 decisions accepted 2026-09-02; kept for the record.)

1. Accept the explicit tie-break (two-sided layouts change vs 2026-08-31
   output, mirror flips only; one-sided unchanged)? The alternative, keeping
   rounding-noise ties, is not unit-invariant and cannot be matched from C.
2. Step 2 cut. Proposed: for convex polygons the set of offsets at which a
   moving mark overlaps a placed one is an interval, computed in closed form
   as the crossing of a horizontal line with the Minkowski difference
   polygon (hull of pairwise vertex differences; identical marks make it
   centrally symmetric and computed once per layout). So the seam is
   `contact_interval(dv) -> (lo, hi)` plus `overlaps(da, db)`, and the
   polygon backend is NOT propose/test/search: it is the same greedy with
   intervals in place of tangent pairs. Consequence for Step 3: production
   never needs polygon min-distance; shapely stays a test-only oracle.
   Phi (2-D moves) for polygons would need edge-projection and
   segment-intersection candidates; proposed to leave that unbuilt and
   report. OK to proceed on this cut?

## Session 2 (2026-09-02, later): improve idd-figures in place

Scope set by Bobby: everything inside idd-figures, no new repo, no packaging.
Commits so far: a016b39 (core refactor group), f5e8a0e (C probe group), and
the dispatch commit a54b60f. `.claude/` contents are gitignored in this
repo; on Bobby's decision (2026-09-02) this record and the decision render
`beeswarm_extraction_star_hull_vs_decompose_v2.png` are negated back in
(`.claude/*` + `!file`), the rest of `.claude/` stays local.

### A-remaining (done)

- **Backend dispatch** at the Step 1 seam: `layout(..., backend="auto"|"c"|
  "python")`, `has_fast_backend()`, `beeswarm_c.available()` (never builds),
  `build()` explicit. "c" raises RuntimeError when absent and
  NotImplementedError for configurations without a C engine; "auto" falls
  back silently. Threaded through the three wrapper entry points. Tests for
  every branch; 140 tests pass.
- **Circle-via-64-gon anchor** (test): the inscribed 64-gon's forbidden
  intervals lie inside the circle's, the circumscribed one's between the
  circle's and those of the disk of radius 1 + (1/cos(pi/64) - 1); its
  metrics bracket the circle's; a layout with it has extent within 1% of the
  circle's. First attempt used the wrong bound (radial excess does not bound
  horizontal excess near the top of the disk); corrected.
- **Hull-vs-decompose visual test, run twice.** First run bound at the size
  floor in four of six panels (informative anyway: at equal marker size the
  hull swarm was 30-36% wider). Second run with floor lowered, stars at
  realistic sizes, margin 0.45, two categories, gap 0.1, auto-sized:

  | dots/category | hull marker | decompose marker | linear ratio | area ratio |
  |---|---|---|---|---|
  | 8 | 15.1 pt | 18.4 pt | 1.22 | 1.49 |
  | 16 | 9.4 pt | 12.4 pt | 1.33 | 1.76 |
  | 30 | 5.5 pt | 8.2 pt | 1.51 | 2.28 |

  Renders: `.claude/beeswarm_extraction_star_hull_vs_decompose_v2.png`
  (and `_v2`-less first run). Looking at them: at 16/category the decompose
  stars are plainly bigger and their arms interleave; at 30/category the
  hull stars are small and evenly spaced like circles while the decompose
  stars are visibly larger and denser. Not a subtle effect.

  **DECISION (called shot): decompose earns its place. It is IN for Step C.**
  At realistic sizes the hull packs stars as their pentagon-ish hull and
  wastes 20-50% of linear marker size; decomposition recovers it visibly.
  Hull stays the default (cheaper, one interval); decompose is opt-in per
  call, and the C polygon path in Step C includes the decomposition-union
  case.

- **Python polygon timings (measured, one layout, one-sided, 3 categories,
  backend="python"):**

  | n | shape | ascending | spine-drop |
  |---|---|---|---|
  | 100 | circle | 0.008 s | 0.019 s |
  | 100 | square | 0.015 s | 0.035 s |
  | 100 | star/hull | 0.012 s | 0.031 s |
  | 100 | star/decompose (25 K) | 0.100 s | 0.240 s |
  | 300 | circle | 0.009 s | 0.033 s |
  | 300 | square | 0.023 s | 0.081 s |
  | 300 | star/hull | 0.026 s | 0.170 s |
  | 300 | star/decompose | 0.343 s | 1.22 s |
  | 1000 | circle | 0.034 s | 0.184 s |
  | 1000 | square | 0.084 s | 0.444 s |
  | 1000 | star/hull | 0.099 s | not run |
  | 1000 | star/decompose | 1.41 s | not run |

  Convex polygons cost 2-3x the circle; decomposition costs 10-15x the
  circle because every neighbour evaluation cuts 25 Minkowski polygons. With
  15-50 optimizer steps, a decomposed-star plot at n=300 is 5-60 s in
  Python. That is the concrete case for the polygon path in C (Step C).

### B: spine-drop in C (done)

**Built.** `bs_spine_drop` in `_c/beeswarm_core.c` (+~210 lines; kernel now
511 lines): stable index sort by (category, value, index) via qsort with a
tie-breaking comparator (equivalent to numpy's stable argsort per category),
spine construction, bins by searchsorted-left, bin walk orders (middle-out
by (far-endpoint distance, lower endpoint), ascending, descending), one
queue per bin, and the lower-bound cache with re-evaluation of the apparent
winner until it still beats the runner-up's cached key. The Python key tuple
(|shift|, cost, value, index) with (inf,) for infeasible became a comparator
over per-point arrays with a feasibility flag. `queue.remove` became a
removed flag; dicts became arrays indexed by point id. Bridge
`beeswarm_c.spine_drop`; dispatch now routes spine-drop (with or without
phi) to C for circles; `backend="c"` no longer refuses it.

**What fought.** Less than expected. The engine is intricate but its state
is all per-point, so arrays replace every dict and list. The one design
choice was the winner/runner-up selection: Python re-sorts the whole queue
each round; C does two linear min scans with the same comparator, which is
equivalent because the keys are unique (the index is the last tuple
element). Compiled clean under -Wall -Wextra on the first build; parity was
exact on the first run.

**Parity (measured).** 18 new parity cases (phi none / 0.7 / 3.0 x two-sided
/ one-sided x three bin orders) plus dispatch tests: all pass. On the timing
data below, max |difference| between Python and C layouts = 0.0 for every
configuration, including spine-drop+phi.

**Speed (measured, same data and figure both backends; 3 categories, 8 x 8 in,
gap 0.1, two-sided, phi frame-bounded; the setup of the first session's
33 s baseline). One layout:**

| n | s | path | Python | C | speedup |
|---|---|---|---|---|---|
| 100 | 250 | spine-drop | 0.029 s | 0.0028 s | 10x |
| 100 | 250 | spine-drop + phi=1 | 0.231 s | 0.0042 s | 55x |
| 300 | 120 | spine-drop | 0.054 s | 0.0033 s | 16x |
| 300 | 120 | spine-drop + phi=1 | 1.22 s | 0.158 s | 8x |
| 1000 | 40 | spine-drop | 0.379 s | 0.037 s | 10x |
| 1000 | 40 | spine-drop + phi=1 | **38.2 s** | **3.19 s** | **12x** |

The 38.2 s row is the same data class as the earlier 33 s baseline (same
seed sequence, different draw order), so this is a true before/after.

**Per plot (measured, C only, `find_optimal_s`, spine-drop + phi=1, margin
0.5, s_min=20):** n=300: 2.5 s in 25 iterations. n=1000: 190 s in 50
iterations (the cap; best_s=23 sits near the floor, the Step 1 flag again).
Derived Python per plot at n=1000: ~50 x 38 s = ~32 min.

**Reading.** C moves spine-drop+phi at n=1000 from unusable (38 s per
layout, ~half an hour per plot) to slow-but-usable (3.2 s per layout, ~3
minutes per plot under the naive 50-step optimizer). At n <= 300 it is
seconds per plot. The speedup pattern is the same as the other engines:
55x where interpreter overhead dominates (n=100), ~10x where the O(m^2)
arithmetic dominates (n=1000). The remaining per-plot factor at n=1000 is
the outer search (roadmap item 1), which multiplies the C gain rather than
competing with it.
