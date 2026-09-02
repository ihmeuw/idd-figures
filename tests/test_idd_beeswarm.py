"""Smoke/regression tests for the idd_beeswarm layout engines (2026-08-31 API).

Distilled from the session audit battery that drove the rewrite: processing
orders, grid methods, phi-penalized value moves. Invariants covered:

- no two dots ever closer than the VISUAL collision diameter (stroke + gap);
- phi -> infinity reproduces the value-exact greedy layout bit-for-bit;
- no dot is left hovering above a valid straight-down landing (the 2026-08-31
  constraint-line candidate fix);
- value coordinates are exact unless a mode explicitly moves them (grids
  quantize; phi trades); the frame is a hard bound on phi's value moves;
- hand-checkable processing orders and the input-validation errors.

The full painter (find_optimal_s / idd_beeswarm) is exercised once; layout
tests call position_all_points directly at fixed s to stay fast. A proper
per-function suite lands with the beeswarm vignette.
"""

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from idd_figures.beeswarm_core import (
    _middle_out_order,
    _processing_order,
    _spine_bin_order,
)
from idd_figures.idd_beeswarm import SCATTER_LW, idd_beeswarm, position_all_points

TOL_PX = 1e-6  # pixel epsilon for the oracle checks below

N = 60
S_FIXED = 70.0
GAP = 0.1


@pytest.fixture
def data():
    rng = np.random.default_rng(7)
    y = rng.normal(0.0, 1.0, N)
    return np.zeros(N), y


@pytest.fixture
def fig_ax(data):
    _, y = data
    fig, ax = plt.subplots(figsize=(8, 2.8))
    r = y.max() - y.min()
    ax.set_xlim(y.min() - 0.2 * r, y.max() + 0.2 * r)
    ax.set_ylim(-0.15, 1.9)
    yield fig, ax
    plt.close(fig)


def _visual_diam(s, fig, gap=GAP):
    return (np.sqrt(s) + SCATTER_LW) * fig.dpi / 72.0 * (1.0 + gap)


def _min_pair_dist_px(res, ax):
    p = ax.transData.transform(res[["xnew", "ynew"]].to_numpy())
    d2 = np.sum((p[:, None, :] - p[None, :, :]) ** 2, axis=-1)
    np.fill_diagonal(d2, np.inf)
    return float(np.sqrt(d2.min()))


def _droppable_count(res, s, fig, ax, one_sided=True):
    """Dots with a strictly lower valid position straight down at their value."""
    p = ax.transData.transform(res[["xnew", "ynew"]].to_numpy())
    val, off = p[:, 0], p[:, 1]
    anchor = ax.transData.transform([(0.0, 0.0)])[0][1]
    d_coll = _visual_diam(s, fig)
    n = 0
    for i in range(val.size):
        oth = np.arange(val.size) != i
        dv = val[oth] - val[i]
        near = np.abs(dv) < d_coll
        cur = abs(off[i] - anchor)
        best = 0.0
        if near.any():
            na, ndv = off[oth][near] - anchor, dv[near]
            da = np.sqrt(d_coll * d_coll - ndv * ndv)
            cands = np.concatenate([[0.0], na + da, na - da])
            if one_sided:
                cands = cands[cands >= -TOL_PX]
            d2 = (cands[:, None] - na[None, :]) ** 2 + (ndv * ndv)[None, :]
            ok = (d2 >= (d_coll - TOL_PX) ** 2).all(axis=1)
            valid = np.abs(cands[ok])
            best = valid.min() if valid.size else np.inf
        if best < cur - 0.5:
            n += 1
    return n


class TestProcessingOrders:
    def test_middle_out_hand_case(self):
        x = np.zeros(5)
        y = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        assert list(y[_middle_out_order(x, y)]) == [30.0, 40.0, 20.0, 50.0, 10.0]

    def test_named_orders_and_vector(self):
        x = np.zeros(4)
        y = np.array([1.0, 2.0, 3.0, 4.0])
        assert list(y[_processing_order(x, y, "ascending")]) == [1.0, 2.0, 3.0, 4.0]
        assert list(y[_processing_order(x, y, "descending")]) == [4.0, 3.0, 2.0, 1.0]
        assert list(y[_processing_order(x, y, [3, 2, 1, 0])]) == [4.0, 3.0, 2.0, 1.0]

    def test_spine_hand_case_with_end_bin(self):
        # D=1.5: spine = 2, 3.5, 0; bins fill middle-out; 4.2 is in the open
        # end bin, judged by its finite endpoint
        x = np.zeros(6)
        vpx = np.array([0.0, 1.0, 2.0, 3.0, 3.5, 4.2])
        got = list(vpx[_spine_bin_order(x, vpx, 1.5)])
        assert got == [2.0, 3.5, 0.0, 3.0, 4.2, 1.0]

    def test_validation_errors(self):
        x = np.zeros(3)
        y = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="permutation"):
            _processing_order(x, y, [0, 0, 1])
        with pytest.raises(ValueError, match="process_order"):
            _processing_order(x, y, "sideways")
        with pytest.raises(ValueError, match="bin_order"):
            _spine_bin_order(x, y, 1.5, bin_order="sideways")


SWARM_MODES = [
    {"process_order": "ascending"},
    {"process_order": "middle-out"},
    {"process_order": "spine"},
    {"process_order": "spine-drop"},
    {"process_order": "spine-drop", "phi": 3.0},
    {"process_order": "middle-out", "phi": 3.0},
]
GRID_METHODS = ["center", "hex", "square"]


class TestLayoutInvariants:
    @pytest.mark.parametrize("kw", SWARM_MODES)
    def test_swarm_modes_never_overlap(self, data, fig_ax, kw):
        x, y = data
        fig, ax = fig_ax
        res, extent = position_all_points(
            x, y, S_FIXED, GAP, fig, ax, orient="h", one_sided=True, **kw
        )
        assert res is not None
        assert _min_pair_dist_px(res, ax) >= _visual_diam(S_FIXED, fig) - 1e-6
        assert np.isfinite(extent)

    @pytest.mark.parametrize("method", GRID_METHODS)
    def test_grids_never_overlap_and_quantize(self, data, fig_ax, method):
        x, y = data
        fig, ax = fig_ax
        res, _ = position_all_points(x, y, S_FIXED, GAP, fig, ax, orient="h", method=method)
        assert _min_pair_dist_px(res, ax) >= _visual_diam(S_FIXED, fig) - 1e-6
        # values snap to rows: far fewer distinct positions than points
        assert len(np.unique(np.round(res["xnew"], 9))) < N / 1.5

    def test_phi_huge_equals_value_exact(self, data, fig_ax):
        x, y = data
        fig, ax = fig_ax
        exact, _ = position_all_points(x, y, S_FIXED, GAP, fig, ax, orient="h", one_sided=True)
        huge, _ = position_all_points(
            x, y, S_FIXED, GAP, fig, ax, orient="h", one_sided=True, phi=1e12
        )
        assert np.allclose(exact[["xnew", "ynew"]], huge[["xnew", "ynew"]])

    @pytest.mark.parametrize("phi", [None, 3.0])
    def test_no_hovering_dots(self, data, fig_ax, phi):
        x, y = data
        fig, ax = fig_ax
        res, _ = position_all_points(
            x,
            y,
            S_FIXED,
            GAP,
            fig,
            ax,
            orient="h",
            one_sided=True,
            process_order="spine-drop",
            phi=phi,
        )
        assert _droppable_count(res, S_FIXED, fig, ax) == 0

    def test_no_wiggle_keeps_values_exact(self, data, fig_ax):
        x, y = data
        fig, ax = fig_ax
        res, _ = position_all_points(
            x,
            y,
            S_FIXED,
            GAP,
            fig,
            ax,
            orient="h",
            one_sided=True,
            process_order="spine-drop",
        )
        assert np.allclose(res["xnew"], y)

    def test_phi_respects_frame_bounds(self, data, fig_ax):
        x, y = data
        fig, ax = fig_ax
        res, _ = position_all_points(x, y, 150.0, GAP, fig, ax, orient="h", one_sided=True, phi=1.0)
        r_data = (
            (np.sqrt(150.0) + SCATTER_LW)
            / 2.0
            * fig.dpi
            / 72.0
            / (ax.transData.transform([(1, 0)])[0][0] - ax.transData.transform([(0, 0)])[0][0])
        )
        lo, hi = ax.get_xlim()
        assert res["xnew"].min() - r_data >= lo - 1e-9
        assert res["xnew"].max() + r_data <= hi + 1e-9


class TestFullPainter:
    def test_idd_beeswarm_end_to_end(self, data):
        _, y = data
        df = pd.DataFrame({"value": y, "group": "toy"})
        idd_beeswarm(
            df,
            x_var="group",
            y_var="value",
            color_var="group",
            color_dict={"toy": "#1f6f8b"},
            fig_size=(8, 2.8),
            margin=1.4,
            gap_fraction=GAP,
            orient="h",
            one_sided=True,
            s_min=20,
            process_order="spine-drop",
            max_iterations=8,
        )
        plt.close("all")

    def test_kwarg_validation(self, data):
        _, y = data
        df = pd.DataFrame({"value": y, "group": "toy"})
        base = {
            "x_var": "group",
            "y_var": "value",
            "color_var": "group",
            "color_dict": {"toy": "#1f6f8b"},
        }
        with pytest.raises(ValueError, match="method"):
            idd_beeswarm(df, method="triangle", **base)
        with pytest.raises(ValueError, match="phi"):
            idd_beeswarm(df, phi=-1.0, **base)
        with pytest.raises(ValueError, match="phi"):
            idd_beeswarm(df, phi=3.0, method="hex", **base)


class TestWrapperHelpers:
    def test_diameter_size_round_trip(self):
        from idd_figures.idd_beeswarm import marker_size_from_diameter_px, visual_diameter_px

        for s in (20.0, 70.0, 400.0):
            d = visual_diameter_px(s, 100.0, GAP)
            assert np.isclose(marker_size_from_diameter_px(d, 100.0, GAP), s)
        assert marker_size_from_diameter_px(0.1, 100.0, GAP) == 0.0

    def test_px_per_unit_orient(self, fig_ax):
        from idd_figures.idd_beeswarm import _px_per_unit

        _fig, ax = fig_ax
        ux, uy = _px_per_unit(ax, "v")
        assert _px_per_unit(ax, "h") == (uy, ux)
        with pytest.raises(ValueError, match="orient"):
            _px_per_unit(ax, "diagonal")


class TestMarkerShapes:
    def test_marker_vertices_px(self):
        from idd_figures.beeswarm_shapes import is_convex, signed_area
        from idd_figures.idd_beeswarm import marker_vertices_px

        sq = marker_vertices_px("s", 100.0, 72.0, linewidth=0.0)
        assert len(sq) == 4 and np.isclose(
            abs(signed_area(sq)), 100.0
        )  # side sqrt(s) points at 72 dpi
        stroked = marker_vertices_px("s", 100.0, 72.0, linewidth=2.0)
        assert np.isclose(abs(signed_area(stroked)), 12.0**2)  # side grows by the stroke
        assert not is_convex(marker_vertices_px("*", 100.0, 100.0))
        with pytest.raises(ValueError, match="one filled polygon"):
            marker_vertices_px("+", 100.0, 100.0)

    def test_marker_shape_units(self):
        from idd_figures.beeswarm_shapes import CIRCLE
        from idd_figures.idd_beeswarm import marker_shape

        assert marker_shape("o", 70.0, 100.0, GAP) is CIRCLE
        sq = marker_shape("s", 70.0, 100.0, GAP)
        # a square marker's stroked, gapped side equals the circle's collision
        # diameter: D units by construction
        assert sq.stack_height == pytest.approx(1.0)
        assert sq.half_width == pytest.approx(0.5)
        st_hull = marker_shape("*", 70.0, 100.0, GAP)
        st_dec = marker_shape("*", 70.0, 100.0, GAP, mode="decompose")
        assert st_hull.n_pieces == 1 and st_dec.n_pieces == 5
        # orient="h" transposes the outline into (category, value)
        tri_v = marker_shape("^", 70.0, 100.0, GAP, orient="v")
        tri_h = marker_shape("^", 70.0, 100.0, GAP, orient="h")
        assert np.allclose(tri_h.vertices, tri_v.vertices[:, ::-1])

    @pytest.mark.parametrize("marker", ["s", "^", "D", "*"])
    def test_polygon_markers_never_overlap(self, data, fig_ax, marker):
        from shapely.geometry import Polygon

        from idd_figures.idd_beeswarm import marker_vertices_px

        pytest.importorskip("shapely")
        x, y = data
        fig, ax = fig_ax
        res, extent = position_all_points(
            x,
            y,
            S_FIXED,
            GAP,
            fig,
            ax,
            orient="h",
            one_sided=True,
            marker=marker,
            process_order="spine-drop",
        )
        assert res is not None and np.isfinite(extent)
        verts = marker_vertices_px(marker, S_FIXED, fig.dpi)  # visual outline, no gap
        p = ax.transData.transform(res[["xnew", "ynew"]].to_numpy())
        polys = [Polygon(verts + c) for c in p]
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                assert polys[i].intersection(polys[j]).area < 1e-6
