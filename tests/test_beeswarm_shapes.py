"""Shape backends: circle, convex polygon via Minkowski silhouette, non-convex
via hull or decomposition. shapely (test-only oracle) checks that the
closed-form forbidden intervals agree with actual polygon overlap."""

import numpy as np
import pytest

from idd_figures.beeswarm_core import layout
from idd_figures.beeswarm_shapes import (
    CIRCLE,
    PolygonShape,
    _silhouette,
    convex_hull,
    fan_decompose,
    is_convex,
    minkowski_sum,
    offset_polygon,
    signed_area,
)

shapely = pytest.importorskip("shapely")
from shapely.geometry import Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402


def regular(k, r=0.5, rot=0.0):
    th = rot + 2 * np.pi * np.arange(k) / k
    return np.column_stack([r * np.cos(th), r * np.sin(th)])


def star(k=5, r_out=0.5, r_in=0.2, rot=np.pi / 2):
    th = rot + np.pi * np.arange(2 * k) / k
    r = np.where(np.arange(2 * k) % 2 == 0, r_out, r_in)
    return np.column_stack([r * np.cos(th), r * np.sin(th)])


def random_convex(rng, n=8, scale=0.5):
    return convex_hull(rng.uniform(-scale, scale, (n, 2)))


def overlap_area(P, pa, pb, Q):
    """shapely: area of the overlap of P translated by (pa, pb) with Q at origin."""
    return Polygon(P + np.array([pa, pb])).intersection(Polygon(Q)).area


class TestPrimitives:
    def test_hull_drops_interior_collinear_duplicates(self):
        pts = np.array(
            [[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5], [0.5, 0], [0, 0], [1, 1]], float
        )
        H = convex_hull(pts)
        assert len(H) == 4
        assert signed_area(H) > 0  # counter-clockwise
        assert np.isclose(signed_area(H), 1.0)

    def test_is_convex(self):
        assert is_convex(regular(6))
        assert is_convex(np.array([[0, 0], [1, 0], [2, 0], [2, 1], [0, 1]], float))  # collinear ok
        assert not is_convex(star())

    def test_minkowski_square_square(self):
        S = regular(4, r=np.sqrt(0.5), rot=np.pi / 4)  # unit square
        K = minkowski_sum(S, -S)
        assert np.isclose(signed_area(K), 4.0)
        assert np.allclose(np.abs(K).max(axis=0), [1.0, 1.0])

    def test_silhouette_square(self):
        S = regular(4, r=np.sqrt(0.5), rot=np.pi / 4)
        K = minkowski_sum(S, -S)  # [-1, 1]^2
        idx, lo, hi = _silhouette(K, [0.0, 0.5, -0.999, 1.0, 1.5])
        assert list(idx) == [0, 1, 2]  # 1.0 is a touching (horizontal edge) cut, 1.5 misses
        assert np.allclose(lo, -1.0) and np.allclose(hi, 1.0)

    def test_silhouette_vertex_touch_is_not_forbidden(self):
        D = regular(4, r=0.5)  # diamond, top vertex at b=0.5
        K = minkowski_sum(D, -D)  # diamond with top at b=1
        idx, _lo, _hi = _silhouette(K, [1.0, 1.0 - 1e-12, 0.999])
        assert list(idx) == [2]

    def test_offset_polygon_square(self):
        S = np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]])
        O = offset_polygon(S, 0.1)
        assert np.allclose(np.abs(O), 0.6)
        O2 = offset_polygon(S[::-1], 0.1)  # clockwise input handled
        assert np.isclose(abs(signed_area(O2)), 1.2**2)

    def test_offset_star_keeps_shape_class_and_grows(self):
        st = star()
        O = offset_polygon(st, 0.02)
        assert not is_convex(O)
        assert Polygon(O).contains(Polygon(st))
        # the offset boundary stays exactly one width away from the original
        # region (achieved along every edge; miter corners are farther)
        assert Polygon(O).exterior.distance(Polygon(st)) == pytest.approx(0.02, abs=1e-9)

    def test_fan_decompose_star(self):
        pieces = fan_decompose(star())
        assert len(pieces) == 5
        assert all(is_convex(p) for p in pieces)
        union = unary_union([Polygon(p) for p in pieces])
        assert np.isclose(union.area, Polygon(star()).area)
        assert union.symmetric_difference(Polygon(star())).area < 1e-12

    def test_fan_decompose_rejects_non_star_shaped(self):
        c_shape = np.array([[0, 0], [3, 0], [3, 1], [1, 1], [1, 2], [3, 2], [3, 3], [0, 3]], float)
        with pytest.raises(ValueError, match="star-shaped"):
            fan_decompose(c_shape)


class TestShapeContract:
    def test_circle(self):
        idx, lo, hi = CIRCLE.forbidden(np.array([0.0, 0.6, 1.0, -2.0]))
        assert list(idx) == [0, 1]
        assert np.allclose(hi, [1.0, 0.8]) and np.allclose(lo, -hi)

    def test_square_metrics(self):
        S = PolygonShape(regular(4, r=np.sqrt(0.5), rot=np.pi / 4))
        assert S.convex and S.n_pieces == 1
        assert S.half_height == pytest.approx(1.0)
        assert S.stack_height == pytest.approx(1.0)
        assert S.half_width == pytest.approx(0.5)
        _idx, lo, hi = S.forbidden(np.array([0.3]))
        assert np.allclose([lo[0], hi[0]], [-1.0, 1.0])

    def test_validation(self):
        with pytest.raises(ValueError, match="mode"):
            PolygonShape(regular(4), mode="exact")
        with pytest.raises(ValueError, match="3 distinct"):
            PolygonShape(np.array([[0, 0], [1, 1], [0, 0]], float))

    def test_hull_mode_on_star_is_one_piece_and_looser(self):
        hull = PolygonShape(star(), mode="hull")
        exact = PolygonShape(star(), mode="decompose")
        assert hull.n_pieces == 1 and not hull.convex
        assert exact.n_pieces == 5
        # hull intervals contain the decomposed union at every height
        for dval in np.linspace(-0.95, 0.95, 21):
            _hi, hl, hh = hull.forbidden([dval])
            ei, el, eh = exact.forbidden([dval])
            if ei.size:
                assert hl.min() <= el.min() + 1e-9 and hh.max() >= eh.max() - 1e-9

    @pytest.mark.parametrize("seed", range(6))
    def test_convex_interval_matches_shapely(self, seed):
        rng = np.random.default_rng(seed)
        P = random_convex(rng)
        S = PolygonShape(P)
        for dval in rng.uniform(-S.half_height, S.half_height, 12):
            idx, lo, hi = S.forbidden([dval])
            if idx.size == 0:
                # no interval: sliding P past itself at this height never overlaps
                for a in np.linspace(-2, 2, 41):
                    assert overlap_area(P, a, dval, P) < 1e-12
                continue
            eps = 1e-6
            assert overlap_area(P, lo[0] + eps, dval, P) > 0
            assert overlap_area(P, hi[0] - eps, dval, P) > 0
            assert overlap_area(P, lo[0] - eps, dval, P) < 1e-12
            assert overlap_area(P, hi[0] + eps, dval, P) < 1e-12
            assert overlap_area(P, lo[0], dval, P) < 1e-9  # touching, not overlapping
            assert overlap_area(P, (lo[0] + hi[0]) / 2, dval, P) > 0

    @pytest.mark.parametrize("mode", ["decompose", "hull"])
    def test_star_union_vs_shapely(self, mode):
        st = star()
        S = PolygonShape(st, mode=mode)
        ref = Polygon(st) if mode == "decompose" else Polygon(convex_hull(st))
        for dval in np.linspace(-0.9, 0.9, 13):
            _idx, lo, hi = S.forbidden([dval])
            for a in np.linspace(-1.1, 1.1, 89):
                inside = bool(np.any((a > lo + 1e-7) & (a < hi - 1e-7)))
                near_edge = bool(np.any(np.abs(a - lo) < 1e-6) | np.any(np.abs(a - hi) < 1e-6))
                if near_edge:
                    continue
                overlap = (
                    Polygon(np.asarray(ref.exterior.coords)[:-1] + np.array([a, dval]))
                    .intersection(ref)
                    .area
                    > 1e-12
                )
                assert inside == overlap, (mode, dval, a)

    def test_decomposed_star_forbids_less_than_hull(self):
        st = star()
        hull, exact = PolygonShape(st, "hull"), PolygonShape(st, "decompose")
        # at mid-height the arms interleave: there are offsets forbidden by
        # the hull but free for the true star
        dval = 0.55
        _hi, hl, hh = hull.forbidden([dval])
        _ei, el, eh = exact.forbidden([dval])
        assert (eh.max() - el.min()) < (hh[0] - hl[0])


class TestLayoutsWithShapes:
    @pytest.fixture
    def anchors(self):
        rng = np.random.default_rng(5)
        return rng.integers(0, 2, 50).astype(float), rng.normal(size=50)

    def _no_overlap(self, verts, cat_new, val_new, dx, dy):
        pts = np.column_stack([cat_new / dx, val_new / dy])
        polys = [Polygon(verts + p) for p in pts]
        worst = 0.0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                worst = max(worst, polys[i].intersection(polys[j]).area)
        return worst

    @pytest.mark.parametrize(
        "verts",
        [regular(4, np.sqrt(0.5), np.pi / 4), regular(3), regular(6), star()],
        ids=["square", "triangle", "hexagon", "star"],
    )
    @pytest.mark.parametrize("order", ["ascending", "spine", "spine-drop"])
    @pytest.mark.parametrize("mode", ["hull", "decompose"])
    def test_no_overlap_by_shapely(self, anchors, verts, order, mode):
        cat, val = anchors
        shape = PolygonShape(verts, mode=mode)
        dx, dy = 0.1, 0.12
        out = layout(
            cat, val, dx, dy, shape=shape, process_order=order, one_sided=(order != "spine")
        )
        assert out is not None
        ref = convex_hull(verts) if mode == "hull" else verts
        assert self._no_overlap(ref, out[0], out[1], dx, dy) < 1e-9

    def test_star_decompose_packs_tighter_than_hull(self, anchors):
        cat, val = anchors
        hull = layout(cat, val, 0.1, 0.12, shape=PolygonShape(star(), "hull"))
        exact = layout(cat, val, 0.1, 0.12, shape=PolygonShape(star(), "decompose"))
        assert exact[2] <= hull[2] + 1e-12

    def test_circle_shape_is_the_default_path(self, anchors):
        cat, val = anchors
        a = layout(cat, val, 0.1, 0.12)
        b = layout(cat, val, 0.1, 0.12, shape=CIRCLE)
        assert np.array_equal(a[0], b[0])

    def test_non_circle_guards(self, anchors):
        cat, val = anchors
        sq = PolygonShape(regular(4))
        with pytest.raises(NotImplementedError, match="circles only"):
            layout(cat, val, 0.1, 0.12, shape=sq, phi=1.0)
        with pytest.raises(NotImplementedError, match="circles only"):
            layout(cat, val, 0.1, 0.12, shape=sq, method="hex")
