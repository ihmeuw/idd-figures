"""Auto-sizing beeswarm: greedy min-shift layout, dot size optimized to margin.

Points are processed in ``process_order`` (2026-08-31): ``"ascending"`` (the
default and the original behavior), ``"descending"``, ``"middle-out"`` (per
category: median value first, then alternating one above / one below, working
outward), ``"spine"`` (pack the category line with every no-shift point
first, then fill the gaps bin by bin, walked per ``bin_order`` — see
``_spine_bin_order``), ``"spine-drop"`` (spine first, then each bin
repeatedly places its lowest-landing point — dynamic order, see
``_spine_drop_layout``; with ``phi``, landings may shift in value), or an
explicit index vector. Ascending's
one-directional tangent chains make every stack lean toward increasing value;
middle-out alternates the lean. Each point takes the smallest offset (along
the category axis) that
keeps every pair of dot centers at least one diameter
(plus ``gap_fraction`` of a diameter) apart, measured in pixels;
``find_optimal_s`` binary-searches the largest dot size whose
max |offset| + radius stays within ``margin`` category-axis units.

Layout methods (2026-08-31): ``method="swarm"`` (default) is the greedy,
value-exact layout described above; ``"center"``, ``"hex"``, ``"square"`` are
R beeswarm's deterministic grids — values QUANTIZE to rows and dots land on a
perfect lattice (see ``_grid_layout_px``) — with the same auto-sized ``s``.

Orientation and sidedness (2026-08-28): ``orient="v"`` (default) draws
categories on x and values on y with horizontal offsets — the original
behavior, bit-identical layouts; ``orient="h"`` draws values on x and
categories on y with vertical offsets. ``one_sided=True`` restricts offsets to
the positive side of the category line (right for "v", up for "h").

Vectorized rewrite (2026-08-28): identical algorithm, API, and defaults to the
original implementation, ~1000x faster per layout (one transData.transform for
all points, numpy collision math over the window of possibly-colliding
neighbours, per-colour scatter). Under the default ascending order the
algorithm matches the original except at exact mirror ties (a point tangent
left or right of its anchor with equal |shift|), where this version
deterministically picks the positive side — and except that collision radii
now include the drawn edge stroke (SCATTER_LW; 2026-08-31 fix — the original
let dots at gap_fraction=0.1 render touching), so layouts at a given ``s``
differ slightly from the original's.

Penalized value moves (2026-08-31): ``phi`` prices moving a dot off its value
at doff^2 + phi * dval^2 in pixel units (p_off fixed at 1), letting dense
spots trade a little value fidelity for less category-axis spread; see
``_layout_px_phi``.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TOL_PX = 1e-6  # the original's collision tolerance, in pixels
SCATTER_LW = 2.0  # linewidth (points) of the drawn dots; the stroke straddles
# the marker path, so the VISUAL diameter is sqrt(s) + SCATTER_LW points. The
# layout must use that (2026-08-31 fix: gap_fraction=0.1 dots drew touching).


def _middle_out_order(x, y):
    """Per-category middle-out processing order.

    Within each category: the median-value point first, then alternating one
    above, one below, working outward.
    """
    parts = []
    for cat in np.unique(x):
        idx = np.flatnonzero(x == cat)
        srt = idx[np.argsort(y[idx], kind="stable")]
        n = srt.size
        mid = (n - 1) // 2
        above = srt[mid + 1 :]
        below = srt[:mid][::-1]
        out = np.empty(n, dtype=np.intp)
        out[0] = srt[mid]
        m = min(above.size, below.size)
        out[1 : 1 + 2 * m : 2] = above[:m]
        out[2 : 2 + 2 * m : 2] = below[:m]
        out[1 + 2 * m :] = above[m:] if above.size > m else below[m:]
        parts.append(out)
    return np.concatenate(parts)


def _spine_bin_order(x, val_px, D, bin_order="middle-out"):
    """Two-phase "spine" processing order (2026-08-31), per category.

    Phase 1 builds the spine: the median-value point, then — alternating one
    above, one below — every point that fits at its anchor with no shift
    (>= D from the last spine point on that side, in value pixels). Placed
    first, these all keep shift 0, so the category line is packed as tightly
    as the data allows before any stacking starts. Phase 2 assigns the
    remaining points to the bins between consecutive spine values and emits
    them bin by bin. ``bin_order`` "middle-out" walks bins outward from the
    median — a bin sorts by its endpoint farther from the median (for the two
    bins touching the median, the endpoint that isn't the median), ties going
    to the lower bin — and fills each bin from its median-facing end outward;
    "ascending" / "descending" walk bins, and points within them, by value.
    """
    if bin_order not in ("middle-out", "ascending", "descending"):
        msg = f"bin_order must be 'middle-out', 'ascending', or 'descending', got {bin_order!r}"
        raise ValueError(msg)
    thresh = D - TOL_PX
    parts = []
    for cat in np.unique(x):
        idx = np.flatnonzero(x == cat)
        srt = idx[np.argsort(val_px[idx], kind="stable")]
        v = val_px[srt]
        n = srt.size
        mid = (n - 1) // 2

        up = []
        last = v[mid]
        for j in range(mid + 1, n):
            if v[j] - last >= thresh:
                up.append(j)
                last = v[j]
        down = []
        last = v[mid]
        for j in range(mid - 1, -1, -1):
            if last - v[j] >= thresh:
                down.append(j)
                last = v[j]
        m = min(len(up), len(down))
        spine = [mid]
        for a, b in zip(up[:m], down[:m]):
            spine += [a, b]
        spine += up[m:] if len(up) > m else down[m:]

        spine_sorted = np.sort(np.asarray(spine, dtype=np.intp))
        sv = v[spine_sorted]
        vm = v[mid]
        rest = np.setdiff1d(np.arange(n), spine_sorted, assume_unique=True)
        seq = list(spine)
        if rest.size:
            # bin k spans (sv[k-1], sv[k]); k=0 and k=len(sv) are the open end
            # bins, judged by their single finite endpoint.
            bins: dict[int, list[int]] = {}
            for pos, k in zip(rest, np.searchsorted(sv, v[rest])):
                bins.setdefault(int(k), []).append(int(pos))

            def mid_out_key(k):
                if 0 < k < sv.size:
                    dist = max(abs(sv[k - 1] - vm), abs(sv[k] - vm))
                else:
                    dist = abs(sv[0 if k == 0 else -1] - vm)
                return (dist, sv[k - 1] if k > 0 else -np.inf)

            if bin_order == "ascending":
                keys = sorted(bins)
            elif bin_order == "descending":
                keys = sorted(bins, reverse=True)
            else:  # middle-out: far-endpoint distance, ties to the lower bin
                keys = sorted(bins, key=mid_out_key)
            for k in keys:
                pts = bins[k]  # ascending in value already
                below = k < sv.size and sv[k] <= vm
                if bin_order == "descending" or (bin_order == "middle-out" and below):
                    pts = pts[::-1]
                seq += pts
        parts.append(srt[np.asarray(seq, dtype=np.intp)])
    return np.concatenate(parts)


def _ellipse_closest(qx, qy, alpha, beta):
    """Closest point on the ellipse (x/alpha)^2 + (y/beta)^2 = 1 to each query
    point (interior or exterior), vectorized bisection on the Lagrange
    parameter. Degenerate queries at the center resolve to (+alpha, 0) — the
    positive-offset convention used at mirror ties.
    """
    qx = np.asarray(qx, dtype=float)
    qy = np.asarray(qy, dtype=float)
    sx = np.where(qx >= 0, 1.0, -1.0)
    sy = np.where(qy >= 0, 1.0, -1.0)
    # nudge zero components so both poles of G(t) exist and the root bracket holds
    ax_ = np.maximum(np.abs(qx), 1e-9 * alpha)
    ay_ = np.maximum(np.abs(qy), 1e-9 * beta)
    a2, b2 = alpha * alpha, beta * beta

    def G(t):
        return (alpha * ax_ / (t + a2)) ** 2 + (beta * ay_ / (t + b2)) ** 2 - 1.0

    lo = np.full(ax_.shape, -min(a2, b2) * (1.0 - 1e-12))
    hi = np.full(ax_.shape, max(a2, b2) + alpha * ax_.max(initial=0.0) + beta * ay_.max(initial=0.0))
    for _ in range(25):  # G is monotone decreasing on (lo, inf)
        grow = G(hi) > 0
        if not grow.any():
            break
        hi = np.where(grow, hi * 2.0 + max(a2, b2), hi)
    for _ in range(44):  # interval shrinks ~1e-13x: ample for pixel geometry
        mid = 0.5 * (lo + hi)
        pos = G(mid) > 0
        lo = np.where(pos, mid, lo)
        hi = np.where(pos, hi, mid)
    t = 0.5 * (lo + hi)
    return a2 * ax_ / (t + a2) * sx, b2 * ay_ / (t + b2) * sy


def _phi_best(ai, bi, PA, PB, D, phi, one_sided=False, val_bounds=None):
    """Best position for one point anchored at (ai, bi) against the placed
    dots (PA, PB): the argmin of doff^2 + phi * dval^2 over valid positions —
    the per-point step of ``_layout_px_phi``, reused by the dynamic-order
    engines. Returns (a, b, cost), or None if no valid position exists.
    """
    thresh2 = (D - TOL_PX) ** 2
    sqphi = np.sqrt(phi)
    dv = PB - bi
    near0 = np.abs(dv) < D
    if not near0.any():
        return ai, bi, 0.0
    na, ndv = PA[near0], dv[near0]
    if not ((na - ai) ** 2 + ndv * ndv < thresh2).any():
        return ai, bi, 0.0
    # pure-offset fallback: its cost c0 caps useful value moves
    da = np.sqrt(D * D - ndv * ndv)
    cands0 = np.concatenate([na + da, na - da])
    d2 = (cands0[:, None] - na[None, :]) ** 2 + (ndv * ndv)[None, :]
    ok0 = (d2 >= thresh2).all(axis=1)
    if one_sided:
        ok0 &= cands0 >= ai - TOL_PX
    valid0 = cands0[ok0]
    if valid0.size == 0:
        return None
    best_a = valid0[np.argmin(np.abs(valid0 - ai))]
    best_b = bi
    c0 = (best_a - ai) ** 2

    delta = np.sqrt(c0 / phi)
    nearW = np.abs(dv) < D + delta
    wa, wb = PA[nearW], PB[nearW]
    # candidates: metric projection onto each circle...
    ex, ey = _ellipse_closest(ai - wa, (bi - wb) * sqphi, D, D * sqphi)
    cx = wa + ex
    cy = wb + ey / sqphi
    # ...plus circle-circle intersections
    m = wa.size
    if m >= 2:
        iu, ju = np.triu_indices(m, 1)
        pdx, pdy = wa[ju] - wa[iu], wb[ju] - wb[iu]
        pd2 = pdx * pdx + pdy * pdy
        okp = (pd2 > TOL_PX**2) & (pd2 < 4.0 * D * D)
        if okp.any():
            iu, ju = iu[okp], ju[okp]
            pdx, pdy, pd2 = pdx[okp], pdy[okp], pd2[okp]
            pdist = np.sqrt(pd2)
            h = np.sqrt(np.maximum(D * D - pd2 / 4.0, 0.0))
            mx = (wa[iu] + wa[ju]) / 2.0
            my = (wb[iu] + wb[ju]) / 2.0
            ux, uy = -pdy / pdist, pdx / pdist
            cx = np.concatenate([cx, mx + h * ux, mx - h * ux])
            cy = np.concatenate([cy, my + h * uy, my - h * uy])
    # ...plus circle intersections with the ACTIVE CONSTRAINT LINES: with
    # one_sided the optimum often sits exactly ON the baseline (and with
    # val_bounds, on a frame edge), where unconstrained projections never land
    if one_sided:
        dy2 = D * D - (ai - wa) ** 2
        hit = dy2 > 0
        if hit.any():
            hh = np.sqrt(dy2[hit])
            cy = np.concatenate([cy, wb[hit] + hh, wb[hit] - hh])
            cx = np.concatenate([cx, np.full(2 * hh.size, ai)])
    if val_bounds is not None:
        for vb in val_bounds:
            dx2 = D * D - (vb - wb) ** 2
            hit = dx2 > 0
            if hit.any():
                hh = np.sqrt(dx2[hit])
                cx = np.concatenate([cx, wa[hit] + hh, wa[hit] - hh])
                cy = np.concatenate([cy, np.full(2 * hh.size, vb)])
            if one_sided:  # corner of both constraints
                cx = np.concatenate([cx, [ai]])
                cy = np.concatenate([cy, [vb]])
    cost = (cx - ai) ** 2 + phi * (cy - bi) ** 2
    keep = cost <= c0 * (1.0 + 1e-12)  # dominated moves out
    if one_sided:
        keep &= cx >= ai - TOL_PX
    if val_bounds is not None:
        keep &= (cy >= val_bounds[0]) & (cy <= val_bounds[1])
    cx, cy, cost = cx[keep], cy[keep], cost[keep]
    best_c = c0
    if cx.size:
        dd2 = (cx[:, None] - wa[None, :]) ** 2 + (cy[:, None] - wb[None, :]) ** 2
        cost = np.where((dd2 >= thresh2).all(axis=1), cost, np.inf)
        j = np.argmin(cost)
        if cost[j] < c0 - 1e-12:  # ties keep the value-exact move
            best_a, best_b, best_c = cx[j], cy[j], cost[j]
    return best_a, best_b, best_c


def _drop_at_value(ai, bi, PA, PB, D, one_sided=False):
    """Lowest valid position straight down (no value move) at value ``bi``:
    the smallest |offset - anchor| (non-negative side when ``one_sided``).
    Returns (a, bi, shift^2), or None.
    """
    thresh2 = (D - TOL_PX) ** 2
    dv = PB - bi
    near = np.abs(dv) < D
    if not near.any():
        return ai, bi, 0.0
    na, ndv = PA[near], dv[near]
    if not ((na - ai) ** 2 + ndv * ndv < thresh2).any():
        return ai, bi, 0.0
    da = np.sqrt(D * D - ndv * ndv)
    cands = np.concatenate([na + da, na - da])
    d2 = (cands[:, None] - na[None, :]) ** 2 + (ndv * ndv)[None, :]
    ok = (d2 >= thresh2).all(axis=1)
    if one_sided:
        ok &= cands >= ai - TOL_PX
    valid = cands[ok]
    if valid.size == 0:
        return None
    a = valid[np.argmin(np.abs(valid - ai))]
    return a, bi, (a - ai) ** 2


def _spine_drop_layout(
    x, off_px, val_px, D, phi=None, one_sided=False, val_bounds=None,
    bin_order="middle-out",
):
    """"Spine over and over" (2026-08-31): dynamic lowest-lander placement.

    Per category, place the no-shift spine (as in ``_spine_bin_order``), then
    sweep the bins repeatedly (walked per ``bin_order``): each sweep, every
    non-empty bin places the unplaced point that can LAND LOWEST — straight
    down at its own value when ``phi`` is None, else at the argmin of
    doff^2 + phi * dval^2 (``_phi_best``). Ties: smaller cost, then lower
    value. Unlike the precomputed orders, who places next is re-decided after
    every placement. Returns (new_off_px, new_val_px), or None.
    """
    if bin_order not in ("middle-out", "ascending", "descending"):
        msg = f"bin_order must be 'middle-out', 'ascending', or 'descending', got {bin_order!r}"
        raise ValueError(msg)
    thresh = D - TOL_PX
    n_all = off_px.size
    new_off = off_px.astype(float).copy()
    new_val = val_px.astype(float).copy()
    PA = np.empty(n_all)
    PB = np.empty(n_all)
    k = 0

    def place(i):
        nonlocal k
        if phi is None:
            res = _drop_at_value(off_px[i], val_px[i], PA[:k], PB[:k], D, one_sided)
        else:
            res = _phi_best(
                off_px[i], val_px[i], PA[:k], PB[:k], D, phi,
                one_sided=one_sided, val_bounds=val_bounds,
            )
        return res

    bin_queues = []  # (points list) in the global bin walk order
    for cat in np.unique(x):
        idx = np.flatnonzero(x == cat)
        srt = idx[np.argsort(val_px[idx], kind="stable")]
        v = val_px[srt]
        n = srt.size
        mid = (n - 1) // 2
        up = []
        last = v[mid]
        for j in range(mid + 1, n):
            if v[j] - last >= thresh:
                up.append(j)
                last = v[j]
        down = []
        last = v[mid]
        for j in range(mid - 1, -1, -1):
            if last - v[j] >= thresh:
                down.append(j)
                last = v[j]
        m = min(len(up), len(down))
        spine = [mid]
        for a, b in zip(up[:m], down[:m]):
            spine += [a, b]
        spine += up[m:] if len(up) > m else down[m:]

        for j in spine:  # spine dots stay put (validated like any placement)
            res = place(srt[j])
            if res is None:
                return None
            PA[k], PB[k] = res[0], res[1]
            k += 1
            new_off[srt[j]], new_val[srt[j]] = res[0], res[1]

        spine_sorted = np.sort(np.asarray(spine, dtype=np.intp))
        sv = v[spine_sorted]
        vm = v[mid]
        rest = np.setdiff1d(np.arange(n), spine_sorted, assume_unique=True)
        if rest.size:
            bins: dict[int, list[int]] = {}
            for pos, kk in zip(rest, np.searchsorted(sv, v[rest])):
                bins.setdefault(int(kk), []).append(int(pos))

            def mid_out_key(kk):
                if 0 < kk < sv.size:
                    dist = max(abs(sv[kk - 1] - vm), abs(sv[kk] - vm))
                else:
                    dist = abs(sv[0 if kk == 0 else -1] - vm)
                return (dist, sv[kk - 1] if kk > 0 else -np.inf)

            if bin_order == "ascending":
                keys = sorted(bins)
            elif bin_order == "descending":
                keys = sorted(bins, reverse=True)
            else:
                keys = sorted(bins, key=mid_out_key)
            bin_queues += [[int(srt[j]) for j in bins[kk]] for kk in keys]

    # Placements only ever ADD obstacles, so a cached evaluation is a lower
    # bound on a point's current landing: re-evaluating just the apparent
    # winner (until it still beats the runner-up's bound) selects exactly the
    # true lowest lander without re-evaluating whole bins each sweep.
    INF = (np.inf,)
    cache: dict[int, tuple] = {}

    def eval_point(i):
        res = place(i)
        if res is None:
            cache[i] = (INF, None, None)
        else:
            a, b, cost = res
            cache[i] = ((abs(a - off_px[i]), cost, val_px[i], i), a, b)
        return cache[i]

    while any(bin_queues):
        placed_this_sweep = False
        for queue in bin_queues:
            if not queue:
                continue
            while True:
                for i in queue:
                    if i not in cache:
                        eval_point(i)
                order_q = sorted(queue, key=lambda i: cache[i][0])
                key, a, b = eval_point(order_q[0])
                runner_up = cache[order_q[1]][0] if len(order_q) > 1 else INF
                if key <= runner_up:
                    break
            if key == INF:
                continue  # nothing in this bin can be placed at this size
            i = order_q[0]
            queue.remove(i)
            cache.pop(i, None)
            PA[k], PB[k] = a, b
            k += 1
            new_off[i], new_val[i] = a, b
            placed_this_sweep = True
        if not placed_this_sweep:
            return None  # s too large: some points have no valid position
    return new_off, new_val


def _layout_px_phi(off_px, val_px, order, D, phi, one_sided=False, val_bounds=None):
    """Greedy swarm with 2-D moves under cost = doff^2 + phi * dval^2 (pixels).

    Like ``_layout_px``, but a colliding point may also move along the VALUE
    axis when that is strictly cheaper than the best pure-offset move (ties
    keep the value-exact position). Exact within the greedy: the optimum of
    the convex cost outside the neighbour circles is the anchor, a circle's
    metric-closest boundary point (``_ellipse_closest`` in sqrt(phi)-scaled
    space), or a circle-circle intersection; candidates costlier than the
    pure-offset fallback c0 are dominated, which bounds useful value moves by
    sqrt(c0/phi) and thereby the neighbour window (small phi widens both).
    ``val_bounds`` (lo, hi in value pixels, already inset by the dot radius)
    makes the axis frame a hard constraint on value moves — a dot never moves
    where it would clip; the value-exact fallback is always permitted.
    Returns (new_off_px, new_val_px), or None if some point has no valid
    position.
    """
    n = off_px.size
    new_off = off_px.astype(float).copy()
    new_val = val_px.astype(float).copy()
    PA = np.empty(n)
    PB = np.empty(n)
    k = 0
    for i in order:
        res = _phi_best(
            off_px[i], val_px[i], PA[:k], PB[:k], D, phi,
            one_sided=one_sided, val_bounds=val_bounds,
        )
        if res is None:
            return None
        ai, bi, _ = res
        PA[k], PB[k] = ai, bi
        k += 1
        new_off[i] = ai
        new_val[i] = bi
    return new_off, new_val


def _grid_layout_px(x, off_px, val_px, D, method, one_sided=False):
    """Deterministic grid layouts (R beeswarm's center / hex / square), 2026-08-31.

    Per category, values snap to rows one pitch apart (pitch = D for "center"
    and "square", D*sqrt(3)/2 for "hex" — adjacent hex rows stagger half a
    diameter, so dots in touching rows are exactly D apart), anchored at the
    category's lowest value. Within a row (data order): "center" spreads dots
    symmetrically about the category line (half-lattice offsets for even
    counts); "square" and "hex" stay on the D lattice, the extra dot of an
    even row going to the lower side. ``one_sided`` fills rows from the
    category line outward instead. Unlike "swarm", the VALUE coordinate moves:
    returns (new_off_px, new_val_px) with values quantized to row centers.
    """
    pitch = D * (np.sqrt(3.0) / 2.0) if method == "hex" else D
    new_off = off_px.astype(float).copy()
    new_val = val_px.astype(float).copy()
    for cat in np.unique(x):
        idx = np.flatnonzero(x == cat)
        v = val_px[idx]
        v0 = v.min()
        row = np.rint((v - v0) / pitch).astype(np.intp)
        for r in np.unique(row):
            pts = idx[row == r]
            k = pts.size
            if one_sided:
                cols = np.arange(k, dtype=float)
            elif method == "center":
                cols = np.arange(k) - (k - 1) / 2.0
            else:  # hex, square: stay on the integer lattice
                cols = np.arange(k, dtype=float) - (k // 2)
            off = cols * D
            if method == "hex" and (r % 2):
                off += D / 2.0
            new_off[pts] = off_px[pts] + off
            new_val[pts] = v0 + r * pitch
    return new_off, new_val


def _processing_order(x, y, process_order):
    """Resolve ``process_order`` into an index array over the points.

    Strings: "ascending" (by value, category as tiebreak — the original
    behavior), "descending" (its reverse), "middle-out" (see
    ``_middle_out_order``). Anything else must be an explicit permutation of
    ``range(n)`` giving the processing order directly.
    """
    if not isinstance(process_order, str):
        order = np.asarray(process_order, dtype=np.intp)
        if order.shape != (x.size,) or not np.array_equal(
            np.sort(order), np.arange(x.size)
        ):
            msg = f"process_order vector must be a permutation of range({x.size})"
            raise ValueError(msg)
        return order
    if process_order == "ascending":
        return np.lexsort((x, y))
    if process_order == "descending":
        return np.lexsort((x, y))[::-1]
    if process_order == "middle-out":
        return _middle_out_order(x, y)
    msg = (
        "process_order must be 'ascending', 'descending', 'middle-out', "
        f"'spine', 'spine-drop', or an index vector, got {process_order!r}"
    )
    raise ValueError(msg)


def _layout_px(off_px, val_px, order, D, one_sided=False):
    """Greedy min-shift swarm in pixel space.

    ``off_px`` is the offset axis (dots slide along it), ``val_px`` the value
    axis (fixed). Returns new offset-axis positions, or None if some point has
    no valid position (s too large). ``order`` is the processing order; the
    first point stays put, every later one takes the smallest |shift| —
    smallest non-negative shift when ``one_sided`` — that keeps all center
    distances >= D (within TOL_PX).
    """
    n = off_px.size
    out = off_px.copy()
    PA = np.empty(n)
    PB = np.empty(n)
    k = 0
    thresh2 = (D - TOL_PX) ** 2
    for i in order:
        ai, bi = off_px[i], val_px[i]
        if k:
            dv = PB[:k] - bi
            near = np.abs(dv) < D
            if near.any():
                na, ndv = PA[:k][near], dv[near]
                if ((na - ai) ** 2 + ndv * ndv < thresh2).any():
                    da = np.sqrt(D * D - ndv * ndv)
                    cands = np.concatenate([na + da, na - da])
                    d2 = (cands[:, None] - na[None, :]) ** 2 + (ndv * ndv)[None, :]
                    ok = (d2 >= thresh2).all(axis=1)
                    valid = cands[ok]
                    if one_sided:
                        valid = valid[valid >= off_px[i] - TOL_PX]
                    if valid.size == 0:
                        return None
                    ai = valid[np.argmin(np.abs(valid - ai))]
        PA[k], PB[k] = ai, bi
        k += 1
        out[i] = ai
    return out


def position_all_points(
    x,
    y,
    s,
    gap_fraction,
    fig,
    ax,
    verbose_inner=False,
    orient="v",
    one_sided=False,
    process_order="ascending",
    bin_order="middle-out",
    method="swarm",
    phi=None,
):
    """Lay out one dot size: returns (result df, max |offset| + radius).

    ``x`` is the category coordinate, ``y`` the value, whatever the orient;
    the returned ``xnew``/``ynew`` are PLOT coordinates (for "h" the value
    lands on the plot x-axis and the offset category coordinate on plot y).
    ``method="swarm"`` is the greedy value-exact layout; "center", "hex",
    "square" are the deterministic grids (see ``_grid_layout_px``), which
    quantize the value coordinate and ignore process_order/bin_order.
    ``phi`` (swarm only, > 0) prices value-axis moves at cost
    doff^2 + phi * dval^2 in pixels (see ``_layout_px_phi``); None keeps
    values exact.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    origin = ax.transData.transform([(0.0, 0.0)])[0]
    if orient == "v":
        pts = ax.transData.transform(np.column_stack([x, y]))
        off_px, val_px = pts[:, 0], pts[:, 1]
        unit = ax.transData.transform([(1.0, 0.0)])[0][0] - origin[0]
        val_unit = ax.transData.transform([(0.0, 1.0)])[0][1] - origin[1]
    elif orient == "h":
        pts = ax.transData.transform(np.column_stack([y, x]))  # plot coords: (value, cat)
        off_px, val_px = pts[:, 1], pts[:, 0]
        unit = ax.transData.transform([(0.0, 1.0)])[0][1] - origin[1]
        val_unit = ax.transData.transform([(1.0, 0.0)])[0][0] - origin[0]
    else:
        msg = f"orient must be 'v' or 'h', got {orient!r}"
        raise ValueError(msg)

    # visual radius: the stroke straddles the marker path (see SCATTER_LW)
    r_px = (np.sqrt(s) + SCATTER_LW) / 2.0 * fig.dpi / 72.0
    D = 2.0 * r_px * (1.0 + gap_fraction)

    if phi is not None:
        if method != "swarm":
            msg = f"phi only applies to method='swarm', got method={method!r}"
            raise ValueError(msg)
        if not phi > 0:
            msg = f"phi must be > 0, got {phi!r}"
            raise ValueError(msg)

    if method == "swarm":
        if phi is not None:
            # the axis frame is a hard bound on value moves: full dot inside
            lims = ax.get_ylim() if orient == "v" else ax.get_xlim()
            if orient == "v":
                lim_px = ax.transData.transform([(0.0, lims[0]), (0.0, lims[1])])[:, 1]
            else:
                lim_px = ax.transData.transform([(lims[0], 0.0), (lims[1], 0.0)])[:, 0]
            val_bounds = (lim_px.min() + r_px, lim_px.max() - r_px)
        else:
            val_bounds = None
        if isinstance(process_order, str) and process_order == "spine-drop":
            pair = _spine_drop_layout(
                x, off_px, val_px, D, phi=phi, one_sided=one_sided,
                val_bounds=val_bounds, bin_order=bin_order,
            )
            if pair is None:
                return None, None
            new_px, val_new_px = pair
            val_new = y + (val_new_px - val_px) / val_unit
        else:
            if isinstance(process_order, str) and process_order == "spine":
                order = _spine_bin_order(x, val_px, D, bin_order=bin_order)
            else:
                order = _processing_order(x, y, process_order)
            if phi is None:
                new_px = _layout_px(off_px, val_px, order, D, one_sided=one_sided)
                if new_px is None:
                    return None, None
                val_new = y
            else:
                pair = _layout_px_phi(
                    off_px, val_px, order, D, phi,
                    one_sided=one_sided, val_bounds=val_bounds,
                )
                if pair is None:
                    return None, None
                new_px, val_new_px = pair
                val_new = y + (val_new_px - val_px) / val_unit
    elif method in ("center", "hex", "square"):
        new_px, val_new_px = _grid_layout_px(
            x, off_px, val_px, D, method, one_sided=one_sided
        )
        val_new = y + (val_new_px - val_px) / val_unit
    else:
        msg = f"method must be 'swarm', 'center', 'hex', or 'square', got {method!r}"
        raise ValueError(msg)

    shift = (new_px - off_px) / unit
    cat_new = x + shift
    result = pd.DataFrame(
        {
            "original_index": np.arange(x.size),
            "xorig": x,
            "yorig": y,
            "xnew": cat_new if orient == "v" else val_new,
            "ynew": val_new if orient == "v" else cat_new,
            "shift": shift,
        }
    )
    return result, float(np.abs(shift).max() + r_px / abs(unit))


def find_optimal_s(
    x,
    y,
    gap_fraction,
    margin,
    fig,
    ax,
    tol=1e-4,
    N_seq=5,
    tol_seq=1e-4,
    max_iterations=50,
    verbose_optim_min=False,
    verbose_optim_full=False,
    verbose_inner=False,
    s_min=100,
    s_max=10000,
    orient="v",
    one_sided=False,
    process_order="ascending",
    bin_order="middle-out",
    method="swarm",
    phi=None,
):
    """Binary-search the largest s whose max |offset| + radius fits in margin."""
    best_s = None
    history = []
    seq_errors: list[float] = []
    best_error = None
    max_seq_error = float("inf")
    iteration = 0
    while True:
        iteration += 1
        s_test = (s_min + s_max) / 2.0
        result, extent = position_all_points(
            x, y, s_test, gap_fraction, fig, ax,
            orient=orient, one_sided=one_sided, process_order=process_order,
            bin_order=bin_order, method=method, phi=phi,
        )
        if result is None:
            valid = False
            s_max = s_test
            error = float("inf")
        elif extent > margin:
            valid = False
            s_max = s_test
            error = abs(margin - extent)
        else:
            valid = True
            best_s = s_test
            s_min = s_test
            error = abs(margin - extent)
        if verbose_optim_min:
            print(f"Iteration {iteration}: s = {s_test:.1f} "
                  f"{'ok' if valid else 'fail'} (extent {extent})")
        if valid and (best_error is None or error < best_error):
            best_error = error
            seq_errors.append(error)
            if len(seq_errors) > N_seq:
                seq_errors = seq_errors[-N_seq:]
                max_seq_error = float(np.max(np.abs(
                    [v - seq_errors[-1] for v in seq_errors[:-1]])))
        history.append({"iteration": iteration, "s_test": s_test, "valid": valid,
                        "max_shift_and_radius": extent, "error": error})
        if iteration >= max_iterations:
            break
        if valid and error < tol:
            break
        if max_seq_error < tol_seq and iteration > 15:
            break

    if best_s is None:
        print(f"\n⚠️  WARNING: Could not find valid s within range. "
              f"Using minimum s = {s_min:.1f}")
        best_s = s_min
    final_result, max_extent = position_all_points(
        x, y, best_s, gap_fraction, fig, ax,
        orient=orient, one_sided=one_sided, process_order=process_order,
        bin_order=bin_order, method=method, phi=phi,
    )
    find_optimal_s.history = history
    return best_s, final_result, max_extent, history


def idd_beeswarm(
    data,
    x_var,
    y_var,
    color_var,
    color_dict,
    x_var_order=None,
    ax=None,
    fig=None,
    fig_size=(8, 8),
    ylim=None,
    ylim_stretch=0.2,
    gap_fraction=0.1,
    margin=0.5,
    x_edge_pad=0.5,
    tol=1e-4,
    N_seq=5,
    tol_seq=1e-4,
    max_iterations=50,
    draw_margin=False,
    verbose_optim_min=False,
    verbose_optim_full=False,
    verbose_inner=False,
    s_min=100,
    s_max=10000,
    orient="v",
    one_sided=False,
    process_order="ascending",
    bin_order="middle-out",
    method="swarm",
    phi=None,
):
    """Auto-sized beeswarm of ``y_var`` per ``x_var`` category.

    ``orient="v"``: categories on plot-x, values on plot-y (the original).
    ``orient="h"``: values on plot-x, categories on plot-y.
    ``one_sided=True``: offsets only on the positive side of the category
    line (right for "v", up for "h"); the unused side keeps a small pad.
    ``method``: "swarm" (the greedy, value-exact layout — everything below
    applies to it) or the R-beeswarm deterministic grids "center", "hex",
    "square" (see ``_grid_layout_px``), which QUANTIZE values to row centers
    and ignore ``process_order``/``bin_order``.
    ``phi`` (swarm only, > 0): allow a colliding dot to move along the VALUE
    axis too, choosing the position minimizing doff^2 + phi * dval^2 in
    pixels — larger phi keeps values truer; ties keep the value-exact move;
    None (default) forbids value moves entirely. Avoid tiny phi (the search
    widens as 1/sqrt(phi)).
    ``process_order``: "ascending" (the original), "descending",
    "middle-out", "spine" (pack the category line with every no-shift point
    first, then fill the gaps bin by bin — see ``_spine_bin_order``),
    "spine-drop" (spine first, then each bin repeatedly places whichever of
    its points lands lowest; no value wiggle without ``phi``), or an
    explicit permutation of ``range(n)`` (row positions in ``data``) giving
    the placement order directly. ``bin_order`` ("middle-out", "ascending",
    "descending") sets how "spine"/"spine-drop" walk the bins; ignored
    otherwise.
    ``ylim``/``ylim_stretch`` always describe the VALUE axis, ``margin``/
    ``x_edge_pad`` the category axis, whatever the orientation.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=fig_size)
    elif fig is None:
        fig = ax.get_figure()

    y = data[y_var].values
    if x_var_order is None:
        x_var_order = data[x_var].unique()
    x_mapping = {val: idx for idx, val in enumerate(x_var_order)}
    x = data[x_var].map(x_mapping).values

    if ylim is None:
        y_diff = max(y) - min(y)
        ylim = (min(y) - ylim_stretch * y_diff, max(y) + ylim_stretch * y_diff)
    lo_pad = 0.15 if one_sided else margin + x_edge_pad   # unused side stays slim
    cat_lim = (min(x) - lo_pad, max(x) + margin + x_edge_pad)
    if orient == "v":
        ax.set_ylim(ylim)
        ax.set_xlim(cat_lim)
    else:
        ax.set_xlim(ylim)
        ax.set_ylim(cat_lim)

    optimal_s, final_positions, max_extent, history = find_optimal_s(
        x, y, gap_fraction, margin, fig, ax,
        tol=tol, N_seq=N_seq, tol_seq=tol_seq, max_iterations=max_iterations,
        verbose_optim_min=verbose_optim_min, verbose_optim_full=verbose_optim_full,
        verbose_inner=verbose_inner, s_min=s_min, s_max=s_max,
        orient=orient, one_sided=one_sided, process_order=process_order,
        bin_order=bin_order, method=method, phi=phi,
    )

    final_data = data.join(final_positions[["xnew", "ynew"]])

    if draw_margin:
        line = ax.axvline if orient == "v" else ax.axhline
        for x_pos in sorted(set(x)):
            if not one_sided:
                line(x_pos - margin, color="gray", linestyle=":", linewidth=2)
            line(x_pos + margin, color="gray", linestyle=":", linewidth=2)
            line(x_pos, color="gray", linestyle="-", linewidth=0.5, alpha=0.3)

    for level, sub in final_data.groupby(color_var, sort=False):
        ax.scatter(sub["xnew"], sub["ynew"], s=optimal_s, marker="o",
                   facecolors=color_dict[level], edgecolors=None,
                   linewidths=SCATTER_LW)

    ticks, labels = list(x_mapping.values()), list(x_mapping.keys())
    if orient == "v":
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels)
        ax.set_xlabel("")
    else:
        ax.set_yticks(ticks)
        ax.set_yticklabels(labels)
        ax.set_ylabel("")

    plt.show()
