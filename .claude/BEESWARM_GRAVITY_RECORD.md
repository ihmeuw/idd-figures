# Beeswarm gravity layout: record

Started 2026-09-02, after the build investigation wrapped. Own unit, own wrap.
Scope (Bobby): design -> first-correct Python -> debug -> C port -> notebook ->
debug -> /wrap. Out of scope: tuning, aesthetics, search optimization.

## Design pass (2026-09-02; approved by Bobby with the amendments in section 6)

### 1. What is generalized

Today's phi step (`_phi_best`) places one mark anchored at (ai, bi) by
minimizing, over feasible positions (x, y),

    C_0(x, y) = doff^2 + phi * dval^2,      doff = x - ai,  dval = y - bi,

with feasibility = strictly outside every placed unit circle, x >= ai when
one_sided, lo <= y <= hi when frame-bounded. If the anchor is feasible the
mark stays (cost 0). Otherwise the pure-offset fallback (best x at y = bi)
costs c0, every candidate costlier than c0 is dominated, and the candidates
are the metric projections onto neighbour circles, circle-circle
intersections, and circle-constraint-line hits. Spine-drop uses this step
as its `place()` and ranks landers by the key (|shift|, cost, value, index).

Coordinates are the core's dimensionless ones (collision diameter 1); "the
origin" for a mark is its own category line, offset ai (all anchors sit on
it), so distance-from-origin = |doff|.

### 2. The gravity objective

    C_g(x, y) = doff^2 * (1 + g * kappa * doff^2)          [growth term]
              + phi * dval^2                                 [unchanged]
              - g * beta * rho(x, y)                         [attractive basin]

    rho(x, y) = sum_j  w_j * exp( -((x - PA_j)^2 + (y - PB_j)^2) / (2 sigma^2) )
    w_j       = exp( -|PA_j - ai| / lam )                    ["low-origin" weight]

Parameters, all in D units:
- g >= 0: overall gravity strength. g = 0 gives C_0 exactly.
- kappa (growth): the offset price doubles at |doff| = 1/sqrt(g kappa). The
  marginal trade between value moves and offset moves becomes
  phi : (1 + 2 g kappa doff^2), i.e. the farther out a mark is, the cheaper a
  value move is relative to staying out. That is "the drive to move
  off-value grows with distance from the origin".
- beta (basin depth, D^2), sigma (basin width, D), lam (how fast a placed
  mark's pull fades with its own distance from the category line, D). The
  basin rewards a candidate that sits inside the smoothed density of
  already-placed marks, weighting marks near the category line most.
Placeholder defaults for the unit (tuning is out of scope): kappa = 1,
beta = 1, sigma = 1.5, lam = 2. Only g is required from the user.

Constraints unchanged: placed circles, one_sided, val_bounds are hard.
Fallback unchanged: the pure-offset move at y = bi is always available and
its gravity cost c0_g is the domination reference. Gate unchanged
(proposed, see open choice A): a mark whose anchor is feasible stays put;
gravity decides only WHERE a displaced mark lands.

g -> 0 reduction: C_g -> C_0 term by term; the feasibility rules, the
fallback, the tie-break, and the spine-drop key are shared code, so the
reduction is exact in results, not just in the formula. This is the
correctness anchor and the headline test.

### 3. The domination bound: verdict

Two separate things the current machinery relies on:

(a) The neighbour WINDOW. Any position that beats the fallback satisfies
C_g(x, y) <= c0_g. The basin is bounded below: rho <= W := sum_j w_j (the
Gaussian kernel is <= 1), so C_g >= doff^2 + phi dval^2 - g beta W. Hence

    phi * dval^2 <= c0_g + g beta W     =>  |dval| <= sqrt((c0_g + g beta W) / phi) =: delta_g
    doff^2       <= c0_g + g beta W     =>  |doff| <= sqrt(c0_g + g beta W)          =: Delta_g

and only placed marks with |PB_j - bi| < 1 + delta_g can touch the optimum.
The window SURVIVES in closed form; it is the phi window widened by the
basin's maximum possible bonus g beta W (conservative: W sums all placed
marks; a compact kernel would tighten it, not needed). The growth term only
adds cost, so it cannot enlarge the window. At g = 0 this is exactly the
current bound.

(b) Candidate COMPLETENESS. This does NOT survive. The current candidate
set is complete because the constrained minimum of a convex cost over
"outside all disks" lies on a disk boundary, at a tangency (the metric
projection) or at an intersection. With the basin, C_g is non-convex:
(i) the minimum can lie in the INTERIOR of the feasible region, at a
density peak in free space, touching no circle at all; (ii) on a circle
arc the stationary points of C_g are roots of a transcendental equation
(Gaussians of the arc angle), with no closed form and possibly several
local minima per arc. No candidate-set argument recovers exactness.

Verdict, per the instruction not to rabbit-hole: keep the closed-form
window (a), and replace the candidate set by an EXHAUSTIVE search over the
window: (1) the existing analytic candidates (metric projections,
circle-circle, circle-line, corners), which stay valid feasible points and
are what makes g = 0 exact; (2) boundary samples along every near circle
(M points per circle, keep the feasible ones); (3) an interior grid over
the window box at spacing h (feasible points only); (4) samples along the
active constraint lines. Evaluate C_g at all of them, keep those <= c0_g,
take the minimum with the existing three-key tie-break, accept it only if
it beats c0_g by more than 1e-12 (the current rule). Result: always
feasible (validated exactly, not approximately), and optimal up to the grid
resolution h (a parameter; default 0.05 D). At g = 0 the analytic
candidates dominate every sample except at measure-zero exact ties, so
gravity(g = 0) reproduces phi+drop to the bit in the generic case.
Optional later polish (not this unit): a few projected-descent steps from
the discrete minimum.

Cost: O(k_near * (window area / h^2 + M * k_near)) per placement. Slow in
Python at n = 300 and above; fine as a correct reference; the C port makes
it usable. That is the intended division of labour.

One honest caveat about the baseline itself, found while deriving this:
the current phi candidate set is complete only up to a rare case, a convex
cost restricted to a circle can have TWO local minima (a second, higher one
on the far side), and if the arc holding the global minimum is covered by
another disk the true arc-minimum is that second local minimum, which is
not generated. The sampled-arc candidates in the gravity engine cover this
case automatically; the phi engine keeps its current behaviour (parity
gate) and the caveat is noted, not fixed, here.

### 4. Where it lives

- `beeswarm_core.py`: `_gravity_best(ai, bi, PA, PB, phi, gravity, one_sided,
  val_bounds)` as a sibling of `_phi_best`, sharing the candidate generator
  (refactor `_phi_best` into `_phi_candidates` + selection; the phi parity
  tests guard that refactor). `Gravity` parameter object (g, kappa, beta,
  sigma, lam, h, M). `layout(..., gravity=None)`: None = today; a Gravity with
  g = 0 must equal phi+drop; requires phi (gravity is phi's generalization)
  and method="swarm"; works with precomputed orders (`_layout_phi` with the
  step swapped) and with spine-drop (`place()` swapped; key unchanged).
  Circle shape only (like phi).
- Dispatch: Python only until the C port lands; then C-capable like phi.
- `beeswarm_c.py` / `_c/beeswarm_core.c`: `gravity_best` mirroring the
  Python; parity target 1e-9, NOT 0.0: the basin uses exp(), and numpy's
  vectorized exp and libm's exp can differ by an ulp, unlike sqrt which is
  correctly rounded in both. Every other engine stayed bit-exact because
  they use only +, *, /, sqrt.
- Tests: g = 0 equals phi+drop (`_layout_phi` and spine-drop paths, random
  data, one-sided and two-sided, bounded and not); no overlaps for g > 0;
  monotonicity in g: mean |doff| of the layout is non-increasing as g grows
  on fixed data (weak form: at g large vs g = 0), and value displacement
  |dval| non-decreasing; window bound never excludes the chosen point
  (assert the winner lies inside Delta_g x delta_g); grid-resolution sanity
  (halving h never increases the found cost).
- Notebook: `notebooks/idd_beeswarm/gravity.ipynb`, a few g values on
  real-ish data (two categories, normal values, spine-drop), side by side.

### 5. Open choices for Bobby (design stop)

A. Gate: a mark whose anchor is feasible stays put (proposed; preserves
   value fidelity and phi's semantics; the basin then only steers displaced
   marks). Alternative: let the basin pull free marks too (every mark may
   move; stronger "gravity" look; g -> 0 still exact). Proposing the gate.
B. "Origin" = the mark's own category line (offset ai); "low-origin" weight
   w_j decays with the placed mark's |PA_j - ai|. Confirm.
C. Parameter surface: g required; kappa, beta, sigma, lam, h, M with the
   placeholder defaults above. Confirm the count is acceptable for this
   unit (tuning later).
D. Correctness statement: "feasible exactly; optimal up to grid spacing h;
   exact at g = 0". Confirm this is the deliverable.

### 6. Amendments folded in after Bobby's read (2026-09-02, before code)

- **"Optimal up to h" is a different guarantee, not a smaller one.** phi is
  exactly optimal within the greedy; gravity's interior grid makes g > 0
  optimal only to grid resolution. Stated plainly, permanently.
- **h is a quality knob tied to sigma.** A grid coarser than the basin
  width can miss a narrow density peak, so the claim is self-consistent
  only when h resolves sigma. Default h = sigma / 8 (derived, not an
  independent knob); a user-supplied h is validated against sigma / 2 and
  refused above it. The effective surface is g plus four shape knobs
  (kappa, beta, sigma, lam) at defaults, with M (boundary samples per
  circle, default 64) as a resolution setting alongside h.
- **g = 0 is exact independent of h.** Exactness at g = 0 rests on the
  analytic candidates dominating every sample, not on the grid. Recorded
  separately from the g > 0 statement so the anchor never reads as
  approximate.
- **Gate confirmed for v1:** a mark whose anchor is feasible stays put, so
  a sparse plot is untouched and gravity cannot worsen an already-good
  layout. **Scoped-out mode, for the exploration session, not rejected:**
  "basin pulls free marks too" (every mark may move toward density to
  tighten loose regions; g -> 0 stays exact). Not built here.
- **Origin is per-mark, not global.** For the mark being placed, the origin
  is its own category line at offset ai; the basin weight
  w_j = exp(-|PA_j - ai| / lam) grades each placed neighbour by ITS offset
  distance from THIS mark's line. "Low-origin" means near the current
  mark's category line, per placement. Gravity is a local nestling force,
  not attraction to one global low point. The C port must read it this way.
- **kappa and beta are g-coupled.** They enter only as g * kappa and
  g * beta, so g is the single "how much gravity" dial and kappa / beta /
  sigma / lam are shape parameters.
- **Deliverable statement (final):** exactly feasible; exact at g = 0
  independent of h; optimal up to grid spacing h for g > 0, where h
  resolves sigma.
- **Parity discipline:** the gravity parity test uses a 1e-9 tolerance
  (exp is not correctly rounded across numpy and libm); every other
  engine keeps its np.array_equal gate. Gravity's tolerance must not
  loosen the existing exact gates.
- **Anchor-feasible cost in the spine-drop key:** returned as 0.0 (as phi
  does), not as the basin value at the anchor, so the dynamic order among
  free marks is identical to phi+drop at every g. Recorded as a choice.
- **rho sums over ALL placed marks** (exact definition, no truncation), in
  chunks to bound memory. Truncating the Gaussian tail is a later
  optimization, to be done identically in both languages.

## Python implementation (2026-09-02; first-correct, small N)

**Built** in `beeswarm_core.py`: `Gravity` (frozen dataclass: g, kappa=1,
beta=1, sigma=1.5, lam=2, h=None -> sigma/8, M=64, exhaustive=True);
`_gravity_cost` (C_g vectorized over candidates; rho over ALL placed marks in
memory-bounded chunks; at g = 0 the growth factor is exactly 1.0 and the
basin term -0.0, so the value equals phi's cost bit for bit);
`_gravity_reference` (phi's pure-offset fallback position, its gravity cost
c0_g, and the closed-form window delta / Delta); `_gravity_best` (the step:
analytic candidates + valid pure-offset positions + M arc samples per near
circle + interior grid at spacing h + constraint-line samples, all checked
exactly for feasibility, phi's filters and tie-break, accept only if it
beats c0_g); `_layout_gravity` (greedy with the step swapped);
`_spine_drop_layout(..., gravity=)` (place() swapped, key unchanged);
`layout(..., gravity=)` with validation (needs phi; circles only; Python
only, `backend="c"` raises). `_phi_best`'s candidate generation was
extracted into `_phi_candidates` and shared; the 210 prior tests, including
the bit-exact C parity gates, still pass, so the extraction changed nothing.
Wrapper: `gravity=` threaded through the three entry points.

**Headline: g = 0 vs phi+drop.** Two results, both measured on random data:
- `Gravity(0, exhaustive=False)` (phi's candidate set under C_g) reproduces
  `_phi_best` bit for bit at every step (tuple equality), and every
  layout (ascending, middle-out, spine, spine-drop; one- and two-sided) is
  `np.array_equal` to the phi layout. Independent of h.
- `Gravity(0)` (exhaustive) is NEVER worse than phi at any step (cost <=,
  1e-12), and identical wherever the costs agree. It is STRICTLY cheaper at
  2.0% of colliding placements (18 of 904 across six seeds, both
  sidednesses), by a median 1.4% and at most 8.9% of the step cost. Those
  are placements where phi's analytic candidate set missed a feasible arc
  point with lower cost: the "second local minimum on a partially covered
  circle" case flagged in the design, now measured rather than suspected.
  phi is unchanged under its exact parity gate, per decision.

Consequence for the anchor: the shared machinery is verified bit-exact via
the analytic mode; the sampler is verified "never worse, exact when equal".
Bit-exact reproduction of phi+drop at g = 0 by the exhaustive engine is
NOT a property, because phi is not exactly optimal.

**Two tie artefacts found and fixed while getting there.** (1) An arc
sample that coincides with an analytic candidate to 1e-16 (a neighbour
directly above the anchor puts the projection exactly at a sample angle)
won the tie-break on rounding noise. (2) A sample within ~sqrt(TOL) of an
analytic optimum ties it in cost (cost is quadratic near an optimum) and
wins on the coordinate tie-break. Fix for both: samples within 1e-4 D of any
analytic candidate are dropped; nothing is lost since such a sample cannot
improve on the exact point by more than ~1e-8.

**Sanity tests (all pass):** no overlaps for g in {0.5, 2, 10} on ascending
and spine-drop; sparse plots untouched at g = 5 (the gate); every winner
lies inside the closed-form window; with beta = 0 the chosen |offset| never
increases with g per placement (up to h); halving h never finds a worse
cost; validation (needs phi, circles only, Gravity type, C refuses);
wrapper smoke. 34 gravity tests; 244 in total.

**Speed (measured, Python, one layout, one-sided, 2 categories, phi = 2):**

| n | phi spine-drop (python) | gravity g=0 spine-drop | gravity g=1 spine-drop | gravity g=1 ascending |
|---|---|---|---|---|
| 60 | 0.134 s | 0.111 s | 0.338 s | 0.151 s |
| 150 | 0.200 s | 0.236 s | 4.0 s | 2.4 s |
| 300 | 0.519 s | 0.678 s | not run | 18.7 s |

g = 0 costs about what phi costs (the sampler's candidates are all
dominated but still evaluated). g > 0 is 10-40x phi and grows fast with n
because the loose window (W sums ALL placed weights) inflates the grid as
the plot fills. Correct and slow, as specified; the C port is the speed
lever, and a tighter W (compact kernel, or summing weights only over marks
that can reach the window) is the first algorithmic lever for a later
session.

### Anchors, stated precisely (Bobby, 2026-09-02; the wording the C port and any reader anchor on)

Two anchors, two properties, two modes. Do not merge them.

1. **Shared-machinery anchor (bit-exact).** Gravity in analytic-candidate
   mode (`exhaustive=False`) reproduces phi+drop bit for bit: tuple equality
   at every step, `np.array_equal` for every layout, all orders, both
   sidednesses, independent of h. This proves the extraction was faithful:
   pulling phi's candidate generator out and rewiring it through gravity's
   code path changed nothing about phi.
2. **Sampler-correctness anchor (never-worse).** Gravity with the sampler on
   (`exhaustive=True`, the default and the whole point) is never worse than
   phi at any placement and strictly cheaper at ~2% of colliding placements
   (measured 18/904, median 1.4%, max 8.9%), where phi's analytic set misses
   a lower-cost feasible arc point. This proves the sampler is complete
   where the analytic set is not. It is NOT a parity statement and must not
   be written as "gravity(0) matches phi+drop": the 2% is the sampler being
   right, not drift.

phi remains bit-frozen under its own exact parity gate. The 2% is a
"gravity is more complete" fact, not a "phi changed" fact. The design
predicted this case as a risk; the implementation measured it as real.

**Load-bearing detail:** the 1e-4 D dedupe of samples against analytic
candidates is what makes anchor 1 robust. Without it a sample coinciding
with an analytic candidate to 1e-16 (or within the cost-tie radius
~sqrt(TOL)) flips the tie on rounding noise and breaks the bit-exact gate.
Do not "optimize it away". Companion rule, added before the C port: the
pure-offset alternatives enter the candidate pool only when strictly
cheaper than the fallback (cost < c0_g - 1e-12), so at g = 0 the pool is
exactly phi's in both modes and the fallback cannot win a tie against an
analytic candidate that phi would have taken.

**C port acceptance criteria (two gates, mirroring the two tests):**
- C gravity exhaustive vs Python gravity exhaustive: positions within 1e-9
  (exp / cos / sin are not correctly rounded across numpy and libm). The
  real gate; phi is irrelevant to it.
- C gravity analytic at g = 0 vs Python phi: `np.array_equal`. The free
  shared-machinery check that the port itself preserved the machinery.
- The 1e-9 tolerance applies to gravity only; the phi / spine-drop / circle
  / polygon gates stay `np.array_equal`.

**Window-tightening lever for the exploration session (not now):** the
window is sqrt((c0_g + g beta W) / phi) with W = sum over ALL placed weights
w_j = exp(-|PA_j - ai| / lam); far marks contribute negligibly to rho yet
fully to W, so W over-counts and the grid grows with placement count.
Truncating the weight sum at a distance where the kernel cannot reach the
window (or using a compact kernel) shrinks the window without losing
candidates. Must be done identically in Python and C.

## C port (2026-09-02)

**Built** in `_c/beeswarm_core.c` (+~230 lines; kernel now ~820 lines):
`gravity_params` (from an 8-double array: g, kappa, beta, sigma, lam,
spacing, M, exhaustive), `gravity_weights`, `gravity_cost1` (same
evaluation order as the numpy expression: d2o * (1 + (g*kappa)*d2o) +
phi*(dval*dval) - (g*beta)*rho; rho over all placed marks; skipped exactly
when g == 0 or beta == 0), `gravity_best` (gate; phi's fallback rule; the
window; `phi_candidates`, extracted from `phi_best` as a pure move; the
strictly-cheaper pure-offset alternatives; arc samples j-major with
th = (2*pi*m)/M; the interior grid with numpy's arange length rule
ceil((stop - start)/h) and x-major order; constraint-line samples; the
1e-4 dedupe against analytic candidates; phi's filters, validity against
the window marks, tie-break, and acceptance), `bs_layout_gravity`,
`bs_gravity_best`, and `bs_spine_drop_gravity` via a shared
`spine_drop_impl` whose `placer` carries an optional gravity pointer.
Bridge: `layout_gravity`, `gravity_best`, `spine_drop(..., gravity=)`,
`_gravity_args`. Dispatch: gravity is C-capable for circles under "auto".
`M_PI` is not C99; a local constant is used with numpy's evaluation order.

**Gate 1 (the real one), measured.** C gravity exhaustive vs Python gravity
exhaustive at g in {0, 0.7, 3}, both sidednesses, bounded and not, per step
(30 placements each) and per layout (ascending, spine-drop): all within
1e-9. On the timing data the max position difference was 0.0 at n = 60 and
300 and 3e-25 at n = 150: glibc's exp/cos/sin and numpy's agree to the bit
on these inputs in practice, though the gate stays at 1e-9 because that is
not guaranteed.

**Gate 2 (free), corrected wording.** The intended statement "C gravity
analytic at g = 0 equals Python phi bit for bit" was never achievable
cross-language and was a wrong premise, not a port failure: the phi engine's
own C gate has been 1e-7 since the first port because the ellipse
projection's bisection-plus-Newton is not bit-identical across libm and
numpy (measured difference here: 1.1e-16, one ulp). What IS bit-exact, and
is the actual shared-machinery check, is kernel-internal: C gravity in
analytic mode equals the kernel's own `phi_best` at every step (0/80
mismatches), `layout_phi` per layout, and `spine_drop(phi)` for spine-drop,
all `np.array_equal`. Cross-language, C gravity analytic sits within the
standing 1e-7 phi tolerance of Python phi (measured 1.1e-16). The Python
anchors (test_beeswarm_gravity.py) pin `backend="python"` on both sides for
the same reason. The 1e-9 / 1e-7 tolerances apply to gravity and phi only;
swarm, spine-drop-without-phi, and polygon gates stay `np.array_equal`.

**Speed (measured, one layout, one-sided, 2 categories, phi = 2, g = 1,
same data both backends, max |diff| per row 0.0 to 3e-25):**

| n | order | Python | C | speedup |
|---|---|---|---|---|
| 60 | ascending | 0.28 s | 0.18 s | 2x |
| 60 | spine-drop | 0.52 s | 0.16 s | 3x |
| 150 | ascending | 7.2 s | 1.8 s | 4x |
| 150 | spine-drop | 7.5 s | 2.2 s | 3x |
| 300 | ascending | 64.8 s | 12.4 s | 5x |
| 300 | spine-drop | not run | 21.0 s | |
| 600 | ascending | not run | 130 s | |

**Honest reading.** Gravity is the first engine where C buys little: 2-5x,
not 10-60x. The exhaustive step is arithmetic-bound in exp(): thousands of
candidates times every placed mark per placement, and numpy's vectorized
exp is nearly as fast as scalar libm exp, so removing interpreter overhead
barely moves it. The speed lever is algorithmic and language-agnostic, as
the design said: (1) tighten the window (W over-counts far marks; truncate
the weight sum or use a compact kernel), which shrinks the grid
quadratically; (2) truncate rho to marks within a few sigma (identically in
both languages). Neither is this unit's job. As delivered: correct,
adjustable, parity-gated, slow at n >= 300, in both languages.

## Speed levers (2026-09-02)

The "thousands of candidates" per placement is a symptom of a loose bound
and a uniform grid, not intrinsic cost. Two independent levers.

**The uniform interior grid is the deliberate correct-but-slow choice for
this unit.** It is what makes "optimal up to h" a statement about the
whole window rather than about where a sampler happened to look.

**Lever 1, window tightening: APPLIED, lossless.** The original window used
rho <= W = sum_j w_j, i.e. every mark's Gaussian at its peak, although marks
far from the window contribute almost nothing there. Replacement: on the
current window box, rho <= W_eff = sum_j w_j * max_box K_j, where max_box K_j
= exp(-dist(mark_j, box)^2 / (2 sigma^2)). This is a rigorous bound (no
tail is dropped, so no tolerance argument is needed): every winner lies in
the current window by induction from the full-W window, so it lies in the
W_eff window too. Two fixed iterations, identical arithmetic in
`_gravity_reference` and the kernel's `gravity_best`. The full gravity and
C suites (both gates, never-worse, window containment, sanity) are the
proof that no result changed; timings below.

**Lever 2, targeted interior sampling: DEFERRED, top priority for the
exploration session, guarantee-changing.** After Lever 1 the remaining cost
is the uniform interior grid, O(window^2 / h^2) candidates each evaluated
against every placed mark. The basin rho is a sum of Gaussians whose minima
of C_g sit near placed marks, so its minima are locatable without uniform
gridding: sample near basin peaks, or coarse-grid-then-refine, or
gradient-descend from a few seeds, replacing thousands of uniform samples
with tens of targeted ones. The trade: "optimal up to grid spacing h"
becomes "optimal up to the sampler's coverage", which can miss a minimum in
exactly the non-convex configurations gravity exists for. Whether that is
acceptable is a visual question across the parameter space, to be judged
against the uniform-grid reference this unit delivers. Available,
high-value, guarantee-changing: validate against the reference, in both
languages identically. Not a bug.

**Lever 1 result (measured, same data and harness as the C-port table; all
157 gravity + C tests green after the change, so no result moved):**

| n | order | Python before -> after | C before -> after |
|---|---|---|---|
| 60 | ascending | 0.28 -> 0.24 s | 0.18 -> 0.16 s |
| 60 | spine-drop | 0.52 -> 0.43 s | 0.16 -> 0.12 s |
| 150 | ascending | 7.2 -> 6.1 s | 1.8 -> 1.5 s |
| 150 | spine-drop | 7.5 -> 5.9 s | 2.2 -> 1.9 s |
| 300 | ascending | 64.8 -> 56.6 s | 12.4 -> 11.2 s |
| 300 | spine-drop | not run -> 79.1 s | 21.0 -> 16.7 s |

10-20%, lossless. Why not more: the tightened bound is now close to the
truth. Every mark inside the window box has max_box K_j = 1, so W_eff is
essentially the count of marks in and near the box, and with beta = 1 each
such mark is worth a full D^2 of possible bonus. Forty window marks make
the basin legitimately worth ~40 D^2, i.e. shifts of ~6 D, and the window
must admit them. The remaining window size is the PARAMETERS (beta, sigma)
speaking, not slack in the bound: shrinking beta shrinks the window
quadratically, which is tuning (exploration session), and cutting the grid
inside the window is Lever 2. In C, one spine-drop layout at n = 300 is
17 s; Python 79 s.

## Notebook (2026-09-02): `notebooks/idd_beeswarm/gravity.ipynb`

Nine cells, executes headlessly in ~7 s (nbclient, repo venv, C kernel in
use). Two categories, 28 marks each, fixed marker size s = 90 pt, gap 0.1,
phi = 2, spine-drop, two-sided. Three figures:

1. **g sweep at fixed size**, g in {0, 0.5, 2, 8}, same data. Measured on
   the render: mean |offset| 0.115 -> 0.107 -> 0.102 -> 0.094 category
   units; mean |value move| 0.042 -> 0.059 -> 0.104 -> 0.186. Visually the
   swarms narrow and become more columnar as g grows; marks accept larger
   value moves and gather where others sit. Per layout in C: 0.02 -> 0.38 s.
2. **The two terms separately at g = 2**: growth only (beta = 0) gives the
   tightest columns (mean |offset| 0.089, value move 0.094); basin only
   (kappa = 0) gathers toward density with smaller value moves (0.104,
   0.059); both together 0.093 / 0.104.
3. **The anchor, three panels in ONE figure**: phi+drop, gravity g = 0
   analytic, gravity g = 0 exhaustive. Printed: analytic vs phi max
   |difference| 0 (bit-exact, as in the tests); exhaustive vs phi 0.039
   category units (the sampler found a cheaper feasible point at some
   placement and the greedy cascaded; never-worse per placement, as tested).

**A confound found and fixed while debugging:** the first version drew the
exhaustive panel in a separate, differently sized figure. With a fixed
marker size in points the data-to-pixel scale, and therefore the packing,
depends on panel geometry, so the comparison was invalid. All anchor panels
now share one figure and the notebook says so: compare layouts only within
a figure. The same effect explains why the g = 0 panel of the sweep (1 x 4
figure) does not match the anchor figure's panels position for position.

**Also noted:** the notebook's figures are inline only; outputs are stripped
on commit by the nbstripout hook, so it is run to be read. The renders used
for this record are `.claude/gravity_notebook_fig{1,2,3}.png` (local).
