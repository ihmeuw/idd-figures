"""Dimensionless beeswarm layout core (extraction step 1, 2026-09-02).

The geometry lives in an isotropic, dimensionless space in which the
collision diameter is 1. ``layout`` is the boundary: it takes anchors in data
units plus the collision diameter expressed in category-axis units (``dx``)
and value-axis units (``dy``), divides in, runs an engine at D = 1, and
multiplies back out. ``find_optimal_size`` binary-searches the largest
diameter whose layout is valid and fits inside ``margin``. Nothing here knows
about pixels, figures, axes, or markers: a plotting wrapper (``idd_beeswarm``
for matplotlib) supplies ``dx``/``dy`` from its own transform and converts the
chosen diameter back to a marker size.

Engines are the 2026-08-31 algorithms unchanged (see that module's history in
git): the greedy value-exact swarm, the phi-penalized swarm with value moves,
the dynamic "spine-drop" placement, and the R-beeswarm grids. Per-category
logic groups on the raw category coordinate, so the scaling never touches it.
``phi`` is a ratio of penalties (offset^2 + phi * value^2) and is unit-free,
so its meaning is unchanged by the normalization.
"""

import warnings

import numpy as np

from idd_figures.beeswarm_shapes import CIRCLE

TOL = 1e-9  # collision tolerance, in units of the collision diameter


def _pick(values, *prefer):
    """Index of the smallest entry of ``values``; ties within TOL are broken by
    the largest of each ``prefer`` key in turn, first survivor wins. The keys
    are the candidate coordinates, so a mirror tie goes to the positive
    offset side (then the higher value). Without this, ties fell to rounding
    noise and the layout depended on the unit the anchors arrived in
    (observed 2026-09-02: pixel-space vs D-normalized runs mirrored whole
    two-sided stacks); it also gives a second implementation a rule to match.
    """
    idx = np.flatnonzero(values <= values.min() + TOL)
    for key in prefer:
        k = key[idx]
        idx = idx[k >= k.max() - TOL]
    return idx[0]


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


def _spine_bin_order(x, val, D, bin_order="middle-out"):
    """Two-phase "spine" processing order, per category.

    Phase 1 builds the spine: the median-value point, then, alternating one
    above, one below, every point that fits at its anchor with no shift
    (>= D from the last spine point on that side, along the value axis).
    Placed first, these all keep shift 0, so the category line is packed as
    tightly as the data allows before any stacking starts. Phase 2 assigns the
    remaining points to the bins between consecutive spine values and emits
    them bin by bin. ``bin_order`` "middle-out" walks bins outward from the
    median (a bin sorts by its endpoint farther from the median; for the two
    bins touching the median, the endpoint that isn't the median; ties going
    to the lower bin) and fills each bin from its median-facing end outward;
    "ascending" / "descending" walk bins, and points within them, by value.
    """
    if bin_order not in ("middle-out", "ascending", "descending"):
        msg = f"bin_order must be 'middle-out', 'ascending', or 'descending', got {bin_order!r}"
        raise ValueError(msg)
    thresh = D - TOL
    parts = []
    for cat in np.unique(x):
        idx = np.flatnonzero(x == cat)
        srt = idx[np.argsort(val[idx], kind="stable")]
        v = val[srt]
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
        for a, b in zip(up[:m], down[:m], strict=True):
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
            for pos, k in zip(rest, np.searchsorted(sv, v[rest]), strict=True):
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
    point (interior or exterior). Degenerate queries on an axis resolve to
    the positive side (the positive-offset convention used at mirror ties)
    via a 1e-9 nudge of the zero component.

    Solves the Lagrange condition G(s) = 0 in ``s`` = distance of the
    multiplier from its nearer pole (not the multiplier itself): the root of
    an on-axis query lies ~1e-9 from the pole and solving in the raw
    multiplier lost 5 digits to cancellation (found 2026-09-02 by the C-port
    parity check: two correct implementations disagreed at 3e-5). Bisection
    brackets the root, then three Newton steps on the convex decreasing G
    polish it to machine precision.
    """
    qx = np.asarray(qx, dtype=float)
    qy = np.asarray(qy, dtype=float)
    sx = np.where(qx >= 0, 1.0, -1.0)
    sy = np.where(qy >= 0, 1.0, -1.0)
    ax_ = np.maximum(np.abs(qx), 1e-9 * alpha)
    ay_ = np.maximum(np.abs(qy), 1e-9 * beta)
    a2, b2 = alpha * alpha, beta * beta
    m = min(a2, b2)
    da, db = a2 - m, b2 - m  # one of these is exactly zero: no cancellation

    def G(s):
        return (alpha * ax_ / (s + da)) ** 2 + (beta * ay_ / (s + db)) ** 2 - 1.0

    def dG(s):
        return -2.0 * (alpha * ax_) ** 2 / (s + da) ** 3 - 2.0 * (beta * ay_) ** 2 / (s + db) ** 3

    lo = np.full(ax_.shape, 1e-12 * m)
    hi = np.full(
        ax_.shape, max(a2, b2) + m + alpha * ax_.max(initial=0.0) + beta * ay_.max(initial=0.0)
    )
    for _ in range(25):  # G is monotone decreasing on (0, inf)
        grow = G(hi) > 0
        if not grow.any():
            break
        hi = np.where(grow, hi * 2.0 + max(a2, b2), hi)
    for _ in range(44):
        mid = 0.5 * (lo + hi)
        pos = G(mid) > 0
        lo = np.where(pos, mid, lo)
        hi = np.where(pos, hi, mid)
    s = 0.5 * (lo + hi)
    for _ in range(3):  # Newton from the left never overshoots a convex decreasing G
        s = np.maximum(s - G(s) / dG(s), lo)
    return a2 * ax_ / (s + da) * sx, b2 * ay_ / (s + db) * sy


def _phi_best(ai, bi, PA, PB, D, phi, one_sided=False, val_bounds=None):
    """Best position for one point anchored at (ai, bi) against the placed
    dots (PA, PB): the argmin of doff^2 + phi * dval^2 over valid positions,
    the per-point step of ``_layout_phi``, reused by the dynamic-order
    engines. Returns (a, b, cost), or None if no valid position exists.
    """
    thresh2 = (D - TOL) ** 2
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
        ok0 &= cands0 >= ai - TOL
    valid0 = cands0[ok0]
    if valid0.size == 0:
        return None
    best_a = valid0[_pick(np.abs(valid0 - ai), valid0)]
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
        okp = (pd2 > TOL**2) & (pd2 < 4.0 * D * D)
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
        keep &= cx >= ai - TOL
    if val_bounds is not None:
        keep &= (cy >= val_bounds[0]) & (cy <= val_bounds[1])
    cx, cy, cost = cx[keep], cy[keep], cost[keep]
    best_c = c0
    if cx.size:
        dd2 = (cx[:, None] - wa[None, :]) ** 2 + (cy[:, None] - wb[None, :]) ** 2
        cost = np.where((dd2 >= thresh2).all(axis=1), cost, np.inf)
        j = _pick(cost, cx, cy)
        if cost[j] < c0 - 1e-12:  # ties keep the value-exact move
            best_a, best_b, best_c = cx[j], cy[j], cost[j]
    return best_a, best_b, best_c


def _min_shift_position(ai, bi, PA, PB, shape=CIRCLE, one_sided=False):
    """The forbidden-interval consumer: smallest-|shift| offset for a mark
    anchored at (ai, bi) against the placed marks (PA, PB), keeping value bi.

    ``shape.forbidden`` gives, per near neighbour, the relative offset
    interval(s) inside which the two marks overlap (a shape may return several
    per neighbour; the union is implicit). The anchor stays if it is strictly
    inside none. Otherwise the candidates are every interval endpoint, an
    endpoint is valid if it lies strictly inside no interval, and the valid
    candidate with the smallest |shift| wins, ``_pick`` breaking ties toward
    the positive side. For circles this is exactly the tangent-pair algebra
    of the 2026-08-31 code. Returns the offset, or None if nothing is valid.
    """
    dval = bi - PB
    near = np.abs(dval) < shape.half_height
    if not near.any():
        return ai
    idx, lo, hi = shape.forbidden(dval[near])
    if idx.size == 0:
        return ai
    na = PA[near][idx]
    L = na + lo
    H = na + hi
    if not ((ai > L + TOL) & (ai < H - TOL)).any():
        return ai
    cands = np.concatenate([H, L])
    bad = (cands[:, None] > L[None, :] + TOL) & (cands[:, None] < H[None, :] - TOL)
    valid = cands[~bad.any(axis=1)]
    if one_sided:
        valid = valid[valid >= ai - TOL]
    if valid.size == 0:
        return None
    return valid[_pick(np.abs(valid - ai), valid)]


def _drop_at_value(ai, bi, PA, PB, shape=CIRCLE, one_sided=False):
    """Lowest valid position straight down (no value move) at value ``bi``:
    the smallest |offset - anchor| (non-negative side when ``one_sided``).
    Returns (a, bi, shift^2), or None.
    """
    a = _min_shift_position(ai, bi, PA, PB, shape, one_sided)
    if a is None:
        return None
    return a, bi, (a - ai) ** 2


def _spine_drop_layout(
    x,
    off,
    val,
    shape=CIRCLE,
    phi=None,
    one_sided=False,
    val_bounds=None,
    bin_order="middle-out",
):
    """ "Spine over and over": dynamic lowest-lander placement.

    Per category, place the no-shift spine (as in ``_spine_bin_order``), then
    sweep the bins repeatedly (walked per ``bin_order``): each sweep, every
    non-empty bin places the unplaced point that can LAND LOWEST, straight
    down at its own value when ``phi`` is None, else at the argmin of
    doff^2 + phi * dval^2 (``_phi_best``). Ties: smaller cost, then lower
    value. Unlike the precomputed orders, who places next is re-decided after
    every placement. Returns (new_off, new_val), or None.
    """
    if bin_order not in ("middle-out", "ascending", "descending"):
        msg = f"bin_order must be 'middle-out', 'ascending', or 'descending', got {bin_order!r}"
        raise ValueError(msg)
    thresh = shape.stack_height - TOL
    n_all = off.size
    new_off = off.astype(float).copy()
    new_val = val.astype(float).copy()
    PA = np.empty(n_all)
    PB = np.empty(n_all)
    k = 0

    def place(i):
        nonlocal k
        if phi is None:
            res = _drop_at_value(off[i], val[i], PA[:k], PB[:k], shape, one_sided)
        else:  # circle-only (validated by ``layout``); D = 1
            res = _phi_best(
                off[i],
                val[i],
                PA[:k],
                PB[:k],
                1.0,
                phi,
                one_sided=one_sided,
                val_bounds=val_bounds,
            )
        return res

    bin_queues = []  # (points list) in the global bin walk order
    for cat in np.unique(x):
        idx = np.flatnonzero(x == cat)
        srt = idx[np.argsort(val[idx], kind="stable")]
        v = val[srt]
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
        for a, b in zip(up[:m], down[:m], strict=True):
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
            for pos, kk in zip(rest, np.searchsorted(sv, v[rest]), strict=True):
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
            cache[i] = ((abs(a - off[i]), cost, val[i], i), a, b)
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
            return None  # D too large: some points have no valid position
    return new_off, new_val


def _layout_phi(off, val, order, D, phi, one_sided=False, val_bounds=None):
    """Greedy swarm with 2-D moves under cost = doff^2 + phi * dval^2.

    Like ``_layout_swarm``, but a colliding point may also move along the
    VALUE axis when that is strictly cheaper than the best pure-offset move
    (ties keep the value-exact position). Exact within the greedy: the optimum
    of the convex cost outside the neighbour circles is the anchor, a circle's
    metric-closest boundary point (``_ellipse_closest`` in sqrt(phi)-scaled
    space), or a circle-circle intersection; candidates costlier than the
    pure-offset fallback c0 are dominated, which bounds useful value moves by
    sqrt(c0/phi) and thereby the neighbour window (small phi widens both).
    ``val_bounds`` (lo, hi, already inset by the dot radius) makes the axis
    frame a hard constraint on value moves; the value-exact fallback is always
    permitted. Returns (new_off, new_val), or None if some point has no valid
    position.
    """
    n = off.size
    new_off = off.astype(float).copy()
    new_val = val.astype(float).copy()
    PA = np.empty(n)
    PB = np.empty(n)
    for k, i in enumerate(order):  # k = number already placed
        res = _phi_best(
            off[i],
            val[i],
            PA[:k],
            PB[:k],
            D,
            phi,
            one_sided=one_sided,
            val_bounds=val_bounds,
        )
        if res is None:
            return None
        ai, bi, _ = res
        PA[k], PB[k] = ai, bi
        new_off[i] = ai
        new_val[i] = bi
    return new_off, new_val


def _grid_layout(x, off, val, D, method, one_sided=False):
    """Deterministic grid layouts (R beeswarm's center / hex / square).

    Per category, values snap to rows one pitch apart (pitch = D for "center"
    and "square", D*sqrt(3)/2 for "hex": adjacent hex rows stagger half a
    diameter, so dots in touching rows are exactly D apart), anchored at the
    category's lowest value. Within a row (data order): "center" spreads dots
    symmetrically about the category line (half-lattice offsets for even
    counts); "square" and "hex" stay on the D lattice, the extra dot of an
    even row going to the lower side. ``one_sided`` fills rows from the
    category line outward instead. Unlike "swarm", the VALUE coordinate moves:
    returns (new_off, new_val) with values quantized to row centers.
    """
    pitch = D * (np.sqrt(3.0) / 2.0) if method == "hex" else D
    new_off = off.astype(float).copy()
    new_val = val.astype(float).copy()
    for cat in np.unique(x):
        idx = np.flatnonzero(x == cat)
        v = val[idx]
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
            o = cols * D
            if method == "hex" and (r % 2):
                o += D / 2.0
            new_off[pts] = off[pts] + o
            new_val[pts] = v0 + r * pitch
    return new_off, new_val


def _processing_order(x, y, process_order):
    """Resolve ``process_order`` into an index array over the points.

    Strings: "ascending" (by value, category as tiebreak), "descending" (its
    reverse), "middle-out" (see ``_middle_out_order``). Anything else must be
    an explicit permutation of ``range(n)`` giving the processing order.
    """
    if not isinstance(process_order, str):
        order = np.asarray(process_order, dtype=np.intp)
        if order.shape != (x.size,) or not np.array_equal(np.sort(order), np.arange(x.size)):
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


def _layout_swarm(off, val, order, shape=CIRCLE, one_sided=False):
    """Greedy min-shift swarm.

    ``off`` is the offset axis (marks slide along it), ``val`` the value axis
    (fixed). Returns new offset-axis positions, or None if some point has no
    valid position. ``order`` is the processing order; the first point stays
    put, every later one takes the smallest |shift| (smallest non-negative
    shift when ``one_sided``) that leaves it outside every placed mark's
    forbidden interval (``_min_shift_position``).
    """
    n = off.size
    out = off.copy()
    PA = np.empty(n)
    PB = np.empty(n)
    for k, i in enumerate(order):  # k = number already placed
        ai = off[i]
        if k:
            ai = _min_shift_position(ai, val[i], PA[:k], PB[:k], shape, one_sided)
            if ai is None:
                return None
        PA[k], PB[k] = ai, val[i]
        out[i] = ai
    return out


METHODS = ("swarm", "center", "hex", "square")
BACKENDS = ("auto", "c", "python")


def _c_kernel():
    """The compiled kernel module when it is importable AND already built, else
    None. Never triggers a build: "auto" must not compile inside a consumer's
    environment (idd-figures is the first consumer; see beeswarm_c.build)."""
    try:
        from idd_figures import beeswarm_c
    except ImportError:
        return None
    return beeswarm_c if beeswarm_c.available() else None


def has_fast_backend():
    """True when the optional C kernel will be used by ``backend="auto"``."""
    return _c_kernel() is not None


def _resolve_backend(backend, c_capable):
    """Return the kernel module to use, or None for pure Python.

    ``c_capable`` says whether the requested configuration has a C engine at
    all (today: circle shape, swarm method, precomputed orders, with or
    without phi). "auto" takes C when both available and capable, else Python
    silently. "c" raises when the kernel is absent (RuntimeError, with the
    build instruction) or when the configuration has no C engine
    (NotImplementedError); it never falls back. "python" always runs Python.
    """
    if backend not in BACKENDS:
        msg = f"backend must be 'auto', 'c', or 'python', got {backend!r}"
        raise ValueError(msg)
    if backend == "python":
        return None
    kern = _c_kernel()
    if backend == "c":
        if kern is None:
            msg = (
                "backend='c' requested but the compiled kernel is not available; "
                "build it with idd_figures.beeswarm_c.build()"
            )
            raise RuntimeError(msg)
        if not c_capable:
            msg = (
                "backend='c' has no kernel for this configuration (spine-drop, grid "
                "methods, and non-circle shapes run in Python)"
            )
            raise NotImplementedError(msg)
        return kern
    return kern if c_capable else None


def _validate(method, phi, shape=CIRCLE):
    if method not in METHODS:
        msg = f"method must be 'swarm', 'center', 'hex', or 'square', got {method!r}"
        raise ValueError(msg)
    if phi is not None:
        if method != "swarm":
            msg = f"phi only applies to method='swarm', got method={method!r}"
            raise ValueError(msg)
        if not phi > 0:
            msg = f"phi must be > 0, got {phi!r}"
            raise ValueError(msg)
    if shape.kind != "circle":
        if phi is not None:
            msg = "phi (value moves) is implemented for circles only"
            raise NotImplementedError(msg)
        if method != "swarm":
            msg = f"grid method {method!r} is implemented for circles only"
            raise NotImplementedError(msg)


def layout(
    cat,
    val,
    dx,
    dy,
    *,
    method="swarm",
    process_order="ascending",
    bin_order="middle-out",
    one_sided=False,
    phi=None,
    val_frame=None,
    gap_fraction=0.0,
    shape=CIRCLE,
    backend="auto",
):
    """Lay out one collision diameter. Returns (cat_new, val_new, extent) or
    None when some point has no valid position at this size.

    ``cat``/``val``: anchors in data units (category coordinate, value).
    ``dx``/``dy``: the collision diameter (visual diameter times 1 + gap)
    expressed in category-axis and value-axis data units. They may carry the
    sign of the axis direction; the geometry is done in ``cat / dx``,
    ``val / dy``, where the collision diameter is 1 and the space is
    isotropic. ``gap_fraction`` recovers the visual radius, D / (2 (1 + gap)),
    used for ``extent`` (max |shift| + visual radius, in category units) and
    for insetting ``val_frame``, the (lo, hi) value-axis frame that bounds
    phi's value moves. ``shape`` is the mark's collision shape in D units
    (``beeswarm_shapes``; default the unit disk); non-circle shapes support
    the swarm method without phi. ``backend`` selects the optional C kernel:
    "auto" (default) uses it when present for the configurations it covers,
    "c" insists and raises otherwise, "python" never uses it. Results are the
    same either way (parity-tested); only speed differs.
    """
    cat = np.asarray(cat, dtype=float)
    val = np.asarray(val, dtype=float)
    _validate(method, phi, shape)
    is_spine_drop = isinstance(process_order, str) and process_order == "spine-drop"
    kern = _resolve_backend(
        backend, c_capable=(method == "swarm" and shape.kind == "circle" and not is_spine_drop)
    )
    a = cat / dx
    b = val / dy
    r = shape.half_width / (1.0 + gap_fraction)
    val_bounds = None
    if phi is not None and val_frame is not None:
        lo, hi = sorted((val_frame[0] / dy, val_frame[1] / dy))
        val_bounds = (lo + r, hi - r)

    if method == "swarm":
        if is_spine_drop:
            pair = _spine_drop_layout(
                cat,
                a,
                b,
                shape,
                phi=phi,
                one_sided=one_sided,
                val_bounds=val_bounds,
                bin_order=bin_order,
            )
            if pair is None:
                return None
            a_new, b_new = pair
        else:
            if isinstance(process_order, str) and process_order == "spine":
                order = _spine_bin_order(cat, b, shape.stack_height, bin_order=bin_order)
            else:
                order = _processing_order(cat, val, process_order)
            if phi is None:
                if kern is not None:
                    a_new = kern.layout_swarm(a, b, order, one_sided=one_sided)
                else:
                    a_new = _layout_swarm(a, b, order, shape, one_sided=one_sided)
                if a_new is None:
                    return None
                b_new = b
            elif kern is not None:
                pair = kern.layout_phi(a, b, order, phi, one_sided=one_sided, val_bounds=val_bounds)
                if pair is None:
                    return None
                a_new, b_new = pair
            else:
                pair = _layout_phi(
                    a, b, order, 1.0, phi, one_sided=one_sided, val_bounds=val_bounds
                )
                if pair is None:
                    return None
                a_new, b_new = pair
    else:
        a_new, b_new = _grid_layout(cat, a, b, 1.0, method, one_sided=one_sided)

    shift = (a_new - a) * dx
    val_new = val + (b_new - b) * dy
    extent = float(np.abs(shift).max() + r * abs(dx))
    return cat + shift, val_new, extent


def find_optimal_size(
    cat,
    val,
    margin,
    dx_unit,
    dy_unit,
    d_min,
    d_max,
    *,
    gap_fraction=0.0,
    tol=1e-4,
    N_seq=5,
    tol_seq=1e-4,
    max_iterations=50,
    verbose=False,
    **layout_kw,
):
    """Binary-search the largest collision diameter whose layout is valid and
    whose extent (max |shift| + visual radius) stays within ``margin``.

    The search scalar ``d`` is a physical diameter in whatever unit the
    wrapper likes (pixels, mm); ``dx_unit``/``dy_unit`` are the category- and
    value-axis data units per one such physical unit, so the layout at ``d``
    uses ``dx = d * dx_unit``, ``dy = d * dy_unit``. Searches ``[d_min,
    d_max]``. Returns (best_d, result, history): ``result`` is the ``layout``
    tuple at best_d, or None if no diameter in range was valid (then best_d
    is d_min and a RuntimeWarning is issued); ``history`` is a list of dicts
    with keys iteration, d_test, valid, max_shift_and_radius, error.
    ``shape`` (in layout_kw) may be a shape or a callable ``d -> shape``.
    """
    cat = np.asarray(cat, dtype=float)
    val = np.asarray(val, dtype=float)
    shape_spec = layout_kw.pop("shape", CIRCLE)

    def shape_at(d):  # a stroked mark is not scale-invariant, so allow shape(d)
        return shape_spec(d) if callable(shape_spec) else shape_spec

    lo0, hi0 = d_min, d_max
    best_d = None
    history = []
    seq_errors: list[float] = []
    best_error = None
    max_seq_error = float("inf")
    iteration = 0
    while True:
        iteration += 1
        d_test = (d_min + d_max) / 2.0
        out = layout(
            cat,
            val,
            d_test * dx_unit,
            d_test * dy_unit,
            gap_fraction=gap_fraction,
            shape=shape_at(d_test),
            **layout_kw,
        )
        extent = None if out is None else out[2]
        if out is None:
            valid = False
            d_max = d_test
            error = float("inf")
        elif extent > margin:
            valid = False
            d_max = d_test
            error = abs(margin - extent)
        else:
            valid = True
            best_d = d_test
            d_min = d_test
            error = abs(margin - extent)
        if verbose:
            print(
                f"Iteration {iteration}: d = {d_test:.4g} "
                f"{'ok' if valid else 'fail'} (extent {extent})"
            )
        if valid and (best_error is None or error < best_error):
            best_error = error
            seq_errors.append(error)
            if len(seq_errors) > N_seq:
                seq_errors = seq_errors[-N_seq:]
                max_seq_error = float(np.max(np.abs([v - seq_errors[-1] for v in seq_errors[:-1]])))
        history.append(
            {
                "iteration": iteration,
                "d_test": d_test,
                "valid": valid,
                "max_shift_and_radius": extent,
                "error": error,
            }
        )
        if iteration >= max_iterations:
            break
        if valid and error < tol:
            break
        if max_seq_error < tol_seq and iteration > 15:
            break

    if best_d is None:
        warnings.warn(
            f"no valid layout for any collision diameter in [{lo0:.4g}, {hi0:.4g}]; "
            f"using the smallest, {d_min:.4g}",
            RuntimeWarning,
            stacklevel=2,
        )
        best_d = d_min
    final = layout(
        cat,
        val,
        best_d * dx_unit,
        best_d * dy_unit,
        gap_fraction=gap_fraction,
        shape=shape_at(best_d),
        **layout_kw,
    )
    return best_d, final, history
