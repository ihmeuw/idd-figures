"""Collision shapes for the beeswarm core (extraction step 2, 2026-09-02).

One contract, in the core's dimensionless space (collision diameter 1): given
the value-axis separations ``dval = b_moving - b_placed`` to a set of placed
marks, a shape returns the FORBIDDEN OFFSET INTERVALS, the ranges of
``a_moving - a_placed`` at which the two marks overlap. The placement engines
consume a union of such intervals across neighbours already; a shape may
therefore contribute several intervals per neighbour without any change in
the consumer. Three cases collapse onto it:

- ``CircleShape``: one interval per neighbour, the tangent pair
  ``+-sqrt(1 - dval^2)``. Closed form, and exactly the 2026-08-31 algebra.
- ``PolygonShape`` of a convex mark: one interval per neighbour, the
  silhouette of the Minkowski difference ``Q (+) (-P)`` cut by the horizontal
  line at ``dval`` (``_silhouette``). Closed form; ``K`` is built once per
  shape as the hull of pairwise vertex differences.
- ``PolygonShape`` of a non-convex mark: ``mode="hull"`` (default) packs the
  convex hull, one interval, slightly loose where concavities are filled in;
  ``mode="decompose"`` splits the mark into convex pieces (fan from the
  centroid, adjacent pieces merged while the union stays convex) and returns
  one interval per piece pair, up to k^2 per neighbour, which is exact
  non-convex packing under the same consumer.

Load-bearing limitation: the interval approach is exact for convex pieces.
Non-convex marks are exact only up to their decomposition ("decompose") or
approximate under hulling ("hull"). Decomposition requires the mark to be
star-shaped about its centroid (every matplotlib marker is); anything else
raises rather than silently mis-packing. All of this is interval arithmetic
over small polygons: no distance function, no search, no shapely; shapely is
used only as a test oracle.
"""

import numpy as np

TOL = 1e-9  # same tolerance as the core, in collision-diameter units


class CircleShape:
    """The unit disk: collision diameter 1."""

    kind = "circle"
    half_height = 1.0  # |dval| beyond which no contact is possible
    stack_height = 1.0  # |dval| at which marks at equal offset just touch
    half_width = 0.5  # visual half-extent along the offset axis
    n_pieces = 1

    def forbidden(self, dval):
        """(idx, lo, hi): for each neighbour in ``dval`` with |dval| < 1, the
        relative offset interval (lo, hi) inside which the marks overlap."""
        dval = np.asarray(dval, dtype=float)
        idx = np.flatnonzero(np.abs(dval) < 1.0)
        h = np.sqrt(1.0 - dval[idx] ** 2)
        return idx, -h, h


CIRCLE = CircleShape()


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points):
    """Counter-clockwise convex hull (Andrew's monotone chain); collinear and
    duplicate points are dropped. Returns an (m, 2) array, m >= 1."""
    pts = np.unique(np.asarray(points, dtype=float), axis=0)  # sorted by x then y
    if len(pts) <= 2:
        return pts
    lower: list[np.ndarray] = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= TOL * TOL:
            lower.pop()
        lower.append(p)
    upper: list[np.ndarray] = []
    for p in pts[::-1]:
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= TOL * TOL:
            upper.pop()
        upper.append(p)
    return np.asarray(lower[:-1] + upper[:-1])


def is_convex(vertices):
    """True if the closed polygon turns the same way at every vertex (collinear
    vertices allowed)."""
    V = np.asarray(vertices, dtype=float)
    n = len(V)
    signs = set()
    for i in range(n):
        c = _cross(V[i], V[(i + 1) % n], V[(i + 2) % n])
        if abs(c) > TOL * TOL:
            signs.add(np.sign(c))
    return len(signs) <= 1


def signed_area(vertices):
    V = np.asarray(vertices, dtype=float)
    x, y = V[:, 0], V[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def minkowski_sum(P, Q):
    """Minkowski sum of two convex polygons as the hull of pairwise sums.
    O(|P||Q| log) instead of the O(|P|+|Q|) edge merge: marks have a handful
    of vertices and this has no orientation or collinear-edge special cases."""
    P = np.asarray(P, dtype=float)
    Q = np.asarray(Q, dtype=float)
    return convex_hull((P[:, None, :] + Q[None, :, :]).reshape(-1, 2))


def _silhouette(K, heights):
    """Cut the convex polygon ``K`` by the horizontal lines ``b = heights``.

    Returns (idx, lo, hi): for each height that cuts K's interior, its index
    and the a-range of the cut. Vertex touches and single-point cuts (lo ==
    hi) are dropped: touching is not overlapping. Vectorized over heights and
    edges; a horizontal edge lying exactly on the line contributes both its
    endpoints through the vertex term.
    """
    K = np.asarray(K, dtype=float)
    h = np.asarray(heights, dtype=float)
    # only lines strictly inside K's vertical extent cut its interior; a line
    # along a top/bottom edge is edge-to-edge touching (found by the oracle
    # tests 2026-09-02: it was being reported as a full-width interval)
    cand = np.flatnonzero((h > K[:, 1].min() + TOL) & (h < K[:, 1].max() - TOL))
    if cand.size == 0:
        return cand, np.empty(0), np.empty(0)
    hh = h[cand]
    p = K
    q = np.roll(K, -1, axis=0)
    pb = p[None, :, 1] - hh[:, None]  # (m, E)
    qb = q[None, :, 1] - hh[:, None]
    crossing = (pb * qb) < 0.0  # strictly straddling edges
    denom = np.where(crossing, q[None, :, 1] - p[None, :, 1], 1.0)
    t = np.where(crossing, -pb / denom, 0.0)
    a_cross = np.where(crossing, p[None, :, 0] + t * (q[None, :, 0] - p[None, :, 0]), np.nan)
    on_vertex = np.abs(pb) <= TOL  # the line passes through a vertex
    a_vert = np.where(on_vertex, p[None, :, 0], np.nan)
    allx = np.concatenate([a_cross, a_vert], axis=1)
    with np.errstate(all="ignore"):
        lo = np.nanmin(allx, axis=1)
        hi = np.nanmax(allx, axis=1)
    keep = np.isfinite(lo) & (hi - lo > TOL)
    return cand[keep], lo[keep], hi[keep]


def _dedupe_closed(vertices):
    """Drop a repeated closing vertex and consecutive duplicates."""
    V = np.asarray(vertices, dtype=float)
    if len(V) > 1 and np.allclose(V[0], V[-1]):
        V = V[:-1]
    keep = np.ones(len(V), dtype=bool)
    keep[1:] = ~np.all(np.isclose(V[1:], V[:-1]), axis=1)
    return V[keep]


def fan_decompose(vertices):
    """Convex pieces of a simple polygon that is star-shaped about its
    centroid: fan triangles from the centroid, then adjacent pieces merged
    (greedy, one pass) while their union stays convex. Raises ValueError if
    some fan triangle is inverted, i.e. the polygon is not star-shaped about
    its centroid and this decomposition would be wrong."""
    V = _dedupe_closed(vertices)
    if signed_area(V) < 0:
        V = V[::-1]
    c = V.mean(axis=0)
    n = len(V)
    tris = []
    for i in range(n):
        tri = np.array([c, V[i], V[(i + 1) % n]])
        if signed_area(tri) <= TOL * TOL:
            msg = "polygon is not star-shaped about its centroid; cannot fan-decompose"
            raise ValueError(msg)
        tris.append(tri)
    pieces = []
    cur = tris[0]
    for tri in tris[1:]:
        merged = convex_hull(np.vstack([cur, tri]))
        # merge only if the hull adds no area beyond the two pieces
        if np.isclose(
            signed_area(merged), signed_area(cur) + signed_area(tri), rtol=1e-9, atol=TOL
        ):
            cur = merged
        else:
            pieces.append(cur)
            cur = tri
    # try to close the ring: last piece with the first
    merged = convex_hull(np.vstack([cur, pieces[0]])) if pieces else None
    if merged is not None and np.isclose(
        signed_area(merged), signed_area(cur) + signed_area(pieces[0]), rtol=1e-9, atol=TOL
    ):
        pieces[0] = merged
    else:
        pieces.append(cur)
    return [convex_hull(p) for p in pieces]


class PolygonShape:
    """A polygonal mark given by its vertices in collision-diameter units,
    centred on the mark's anchor. ``mode`` is "hull" (default) or
    "decompose"; convex marks are one piece either way."""

    kind = "polygon"

    def __init__(self, vertices, mode="hull"):
        if mode not in ("hull", "decompose"):
            msg = f"mode must be 'hull' or 'decompose', got {mode!r}"
            raise ValueError(msg)
        V = _dedupe_closed(vertices)
        if len(V) < 3:
            msg = f"a polygon needs at least 3 distinct vertices, got {len(V)}"
            raise ValueError(msg)
        self.vertices = V
        self.convex = is_convex(V)
        self.mode = mode
        if self.convex or mode == "hull":
            self.pieces = [convex_hull(V)]
        else:
            self.pieces = fan_decompose(V)
        self.n_pieces = len(self.pieces)
        # K_pq = placed piece q (+) -(moving piece p): the moving mark's
        # centre offset (a, dval) overlaps iff it lies inside some K_pq.
        self.K = [minkowski_sum(q, -p) for p in self.pieces for q in self.pieces]
        allK = np.vstack(self.K)
        self.half_height = float(np.abs(allK[:, 1]).max())
        self.half_width = float(np.abs(V[:, 0]).max())
        # marks at equal offset: forbidden |dval| is the union of the K's
        # vertical silhouettes at a = 0
        tops = []
        for K in self.K:
            idx, lo, hi = _silhouette(K[:, ::-1], [0.0])
            if idx.size:
                tops.append(max(abs(lo[0]), abs(hi[0])))
        self.stack_height = float(max(tops)) if tops else 0.0

    def forbidden(self, dval):
        dval = np.asarray(dval, dtype=float)
        parts = [_silhouette(K, dval) for K in self.K]
        idx = np.concatenate([p[0] for p in parts])
        lo = np.concatenate([p[1] for p in parts])
        hi = np.concatenate([p[2] for p in parts])
        return idx, lo, hi

    def __repr__(self):
        return (
            f"PolygonShape({len(self.vertices)} vertices, "
            f"{'convex' if self.convex else 'non-convex'}, mode={self.mode!r}, "
            f"{self.n_pieces} piece(s))"
        )


def offset_polygon(vertices, width):
    """Dilate a simple polygon by ``width`` with mitered joins: each edge moves
    outward along its normal and consecutive offset edges are re-intersected.
    Exact for a stroke of width 2*width on straight edges and mitered
    corners; reflex vertices (a star's inner corners) miter inward as a real
    stroke join does. Parallel consecutive edges are not expected on marks;
    they raise."""
    V = _dedupe_closed(vertices)
    if signed_area(V) < 0:
        V = V[::-1]
    n = len(V)
    e = np.roll(V, -1, axis=0) - V
    length = np.hypot(e[:, 0], e[:, 1])
    normal = np.column_stack([e[:, 1], -e[:, 0]]) / length[:, None]  # outward for CCW
    p0 = V + width * normal  # offset edge i passes through p0[i] with direction e[i]
    out = np.empty_like(V)
    for i in range(n):
        j = (i - 1) % n  # edges j -> i meet at vertex i
        A = np.column_stack([e[j], -e[i]])
        det = A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0]
        if abs(det) < 1e-14 * length[i] * length[j]:
            msg = "consecutive parallel edges; mitered offset undefined"
            raise ValueError(msg)
        t = np.linalg.solve(A, p0[i] - p0[j])[0]
        out[i] = p0[j] + t * e[j]
    return out
