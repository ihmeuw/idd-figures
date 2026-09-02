"""Unit tests for the dimensionless beeswarm core (extraction step 1)."""

import numpy as np
import pytest

from idd_figures.beeswarm_core import (
    TOL,
    _layout_swarm,
    _pick,
    _validate,
    find_optimal_size,
    layout,
)

MODES = [
    {},
    {"process_order": "middle-out"},
    {"process_order": "spine"},
    {"process_order": "spine-drop"},
    {"process_order": "spine-drop", "phi": 3.0},
    {"process_order": "middle-out", "phi": 3.0},
    {"method": "center"},
    {"method": "hex"},
]


@pytest.fixture
def anchors():
    rng = np.random.default_rng(3)
    cat = rng.integers(0, 3, 90).astype(float)
    val = rng.normal(size=90)
    return cat, val


def _normalized_min_dist(cat_new, val_new, dx, dy):
    p = np.column_stack([cat_new / dx, val_new / dy])
    d2 = np.sum((p[:, None, :] - p[None, :, :]) ** 2, axis=-1)
    np.fill_diagonal(d2, np.inf)
    return float(np.sqrt(d2.min()))


class TestPick:
    def test_min_wins_when_distinct(self):
        assert _pick(np.array([3.0, 1.0, 2.0]), np.array([0.0, 0.0, 0.0])) == 1

    def test_tie_goes_to_largest_prefer_then_first(self):
        vals = np.array([1.0, 1.0 + TOL / 2, 1.0, 5.0])
        assert _pick(vals, np.array([-1.0, 2.0, 2.0, 9.0])) == 1
        assert _pick(vals, np.array([0.0, 0.0, 0.0, 9.0])) == 0
        # second key breaks what the first leaves tied
        assert _pick(vals, np.array([0.0, 0.0, 0.0, 9.0]), np.array([0.0, 1.0, 5.0, 0.0])) == 2


class TestLayout:
    @pytest.mark.parametrize("kw", MODES)
    def test_unit_invariance(self, anchors, kw):
        """Rescaling anchors and diameters together rescales the layout exactly."""
        cat, val = anchors
        dx, dy = 0.08, 0.15
        base = layout(cat, val, dx, dy, one_sided=True, gap_fraction=0.1, **kw)
        k_c, k_v = 3.0, 0.25
        scaled = layout(
            cat * k_c, val * k_v, dx * k_c, dy * k_v, one_sided=True, gap_fraction=0.1, **kw
        )
        assert base is not None and scaled is not None
        assert np.allclose(scaled[0], base[0] * k_c, rtol=1e-9, atol=1e-12)
        assert np.allclose(scaled[1], base[1] * k_v, rtol=1e-9, atol=1e-12)
        assert np.isclose(scaled[2], base[2] * k_c, rtol=1e-9)

    @pytest.mark.parametrize("kw", MODES)
    @pytest.mark.parametrize("one_sided", [False, True])
    def test_never_overlap_in_normalized_space(self, anchors, kw, one_sided):
        cat, val = anchors
        dx, dy = 0.08, 0.15
        out = layout(cat, val, dx, dy, one_sided=one_sided, gap_fraction=0.1, **kw)
        assert out is not None
        assert _normalized_min_dist(out[0], out[1], dx, dy) >= 1.0 - 1e-9

    def test_negative_dx_flips_the_positive_side(self, anchors):
        cat, val = anchors
        pos = layout(cat, val, 0.08, 0.15, one_sided=True)
        neg = layout(cat, val, -0.08, 0.15, one_sided=True)
        assert np.all(pos[0] - cat >= -1e-12)
        assert np.all(neg[0] - cat <= 1e-12)
        assert np.allclose(neg[0] - cat, -(pos[0] - cat))

    def test_values_exact_without_value_moves(self, anchors):
        cat, val = anchors
        for kw in ({}, {"process_order": "spine-drop"}):
            out = layout(cat, val, 0.08, 0.15, **kw)
            assert np.array_equal(out[1], val)

    def test_extent_is_max_shift_plus_visual_radius(self, anchors):
        cat, val = anchors
        dx, gap = 0.08, 0.25
        cat_new, _, extent = layout(cat, val, dx, 0.15, gap_fraction=gap)
        assert np.isclose(extent, np.abs(cat_new - cat).max() + dx / (2 * (1 + gap)))

    def test_mirror_tie_goes_positive(self):
        """Three coincident anchors: second lands at +1, third at -1 (|shift|
        1 beats +2), in D units."""
        a = _layout_swarm(np.zeros(3), np.zeros(3), np.arange(3))
        assert np.allclose(a, [0.0, 1.0, -1.0])

    def test_validation(self):
        with pytest.raises(ValueError, match="method"):
            _validate("triangle", None)
        with pytest.raises(ValueError, match="phi only"):
            _validate("hex", 2.0)
        with pytest.raises(ValueError, match="phi must"):
            _validate("swarm", 0.0)
        with pytest.raises(ValueError, match="process_order"):
            layout(np.zeros(3), np.arange(3.0), 1.0, 1.0, process_order="sideways")


class TestFindOptimalSize:
    def test_fits_margin_and_history(self, anchors):
        cat, val = anchors
        best_d, result, history = find_optimal_size(
            cat, val, 0.45, 0.01, 0.02, 0.5, 60.0, gap_fraction=0.1, one_sided=True
        )
        assert result is not None
        assert result[2] <= 0.45 + 1e-12
        assert history[-1]["d_test"] > 0
        assert {"iteration", "d_test", "valid", "max_shift_and_radius", "error"} <= set(history[0])
        # the layout at best_d is the one returned
        again = layout(cat, val, best_d * 0.01, best_d * 0.02, gap_fraction=0.1, one_sided=True)
        assert np.allclose(again[0], result[0])

    def test_warns_and_falls_back_when_nothing_fits(self, anchors):
        cat, val = anchors
        with pytest.warns(RuntimeWarning, match="no valid layout"):
            best_d, result, _ = find_optimal_size(
                cat, val, 1e-6, 0.01, 0.02, 0.5, 60.0, max_iterations=6
            )
        assert best_d == 0.5
        assert result is not None
