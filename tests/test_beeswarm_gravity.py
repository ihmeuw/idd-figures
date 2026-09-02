"""Gravity layout engine. Headline: g = 0 reproduces phi+drop exactly (shared
gate, fallback, filters, tie-break; analytic candidates dominate samples).
Then sanity for g > 0: feasibility, the closed-form window, monotone growth."""

import numpy as np
import pytest

from idd_figures.beeswarm_core import (
    Gravity,
    _gravity_best,
    _gravity_reference,
    _phi_best,
    _processing_order,
    layout,
)
from idd_figures.beeswarm_shapes import PolygonShape

PHI = 2.0


@pytest.fixture
def anchors():
    rng = np.random.default_rng(17)
    cat = rng.integers(0, 2, 70).astype(float) * 30.0
    val = rng.normal(size=70) * 3.0
    return cat, val


def _min_dist(a, b):
    p = np.column_stack([a, b])
    d2 = np.sum((p[:, None, :] - p[None, :, :]) ** 2, axis=-1)
    np.fill_diagonal(d2, np.inf)
    return float(np.sqrt(d2.min()))


def _placed_sets(cat, val, one_sided, val_bounds, n_steps=40):
    """Placed configurations reached by the phi greedy, for per-step tests."""
    order = _processing_order(cat, val, "ascending")
    PA, PB = np.empty(cat.size), np.empty(cat.size)
    out = []
    for k, i in enumerate(order[:n_steps]):
        out.append((cat[i], val[i], PA[:k].copy(), PB[:k].copy()))
        res = _phi_best(cat[i], val[i], PA[:k], PB[:k], 1.0, PHI, one_sided, val_bounds)
        PA[k], PB[k] = res[0], res[1]
    return out


class TestGravityParams:
    def test_defaults_and_spacing(self):
        g = Gravity(1.0)
        assert g.spacing == pytest.approx(1.5 / 8)
        assert Gravity(1.0, sigma=2.0, h=0.5).spacing == 0.5

    def test_validation(self):
        with pytest.raises(ValueError, match="g must"):
            Gravity(-0.1)
        with pytest.raises(ValueError, match="resolves the basin"):
            Gravity(1.0, sigma=1.0, h=0.6)
        with pytest.raises(ValueError, match="sigma and lam"):
            Gravity(1.0, sigma=0.0)
        with pytest.raises(ValueError, match="kappa and beta"):
            Gravity(1.0, beta=-1.0)


class TestGZeroIsPhi:
    """Two anchors, both Python-internal (backend="python" on both sides: the
    cross-language phi gate is 1e-7 because of the ellipse solve, see
    test_beeswarm_c). Analytic-only gravity at g = 0 IS phi+drop, bit for bit
    (shared gate, fallback, candidates, filters, tie-break). Exhaustive gravity
    at g = 0 is never worse than phi at any step and identical wherever phi's
    analytic set contains the optimum; where the sampler finds a strictly
    cheaper feasible point, phi was suboptimal (its candidate set is complete
    only up to a second local minimum on a partially covered circle)."""

    @pytest.mark.parametrize("one_sided", [False, True])
    @pytest.mark.parametrize("bounded", [False, True])
    def test_analytic_step_is_phi_best_bit_for_bit(self, anchors, one_sided, bounded):
        cat, val = anchors
        vb = (val.min() - 0.2, val.max() + 0.2) if bounded else None
        grav = Gravity(0.0, exhaustive=False)
        for ai, bi, PA, PB in _placed_sets(cat, val, one_sided, vb):
            p = _phi_best(ai, bi, PA, PB, 1.0, PHI, one_sided, vb)
            q = _gravity_best(ai, bi, PA, PB, PHI, grav, one_sided, vb)
            assert p == q

    @pytest.mark.parametrize("one_sided", [False, True])
    @pytest.mark.parametrize("bounded", [False, True])
    def test_exhaustive_step_never_worse_than_phi(self, anchors, one_sided, bounded):
        cat, val = anchors
        vb = (val.min() - 0.2, val.max() + 0.2) if bounded else None
        grav = Gravity(0.0)
        for ai, bi, PA, PB in _placed_sets(cat, val, one_sided, vb):
            p = _phi_best(ai, bi, PA, PB, 1.0, PHI, one_sided, vb)
            q = _gravity_best(ai, bi, PA, PB, PHI, grav, one_sided, vb)
            assert q[2] <= p[2] + 1e-12
            if abs(q[2] - p[2]) <= 1e-12:
                assert (q[0], q[1]) == (p[0], p[1])

    @pytest.mark.parametrize("order", ["ascending", "middle-out", "spine", "spine-drop"])
    @pytest.mark.parametrize("one_sided", [False, True])
    def test_analytic_layout_is_phi_layout(self, anchors, order, one_sided):
        cat, val = anchors
        ref = layout(
            cat, val, 0.5, 0.6, phi=PHI, process_order=order, one_sided=one_sided, backend="python"
        )
        got = layout(
            cat,
            val,
            0.5,
            0.6,
            phi=PHI,
            process_order=order,
            one_sided=one_sided,
            gravity=Gravity(0.0, exhaustive=False),
            backend="python",
        )
        assert np.array_equal(ref[0], got[0]) and np.array_equal(ref[1], got[1])

    def test_analytic_g_zero_independent_of_h(self, anchors):
        cat, val = anchors
        a = layout(
            cat,
            val,
            0.5,
            0.6,
            phi=PHI,
            process_order="spine-drop",
            gravity=Gravity(0.0, h=0.05, exhaustive=False),
        )
        b = layout(
            cat,
            val,
            0.5,
            0.6,
            phi=PHI,
            process_order="spine-drop",
            gravity=Gravity(0.0, h=0.75, exhaustive=False),
        )
        assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])

    def test_exhaustive_g_zero_layouts_are_valid_and_no_costlier(self, anchors):
        """Layout-level: exhaustive g = 0 stays feasible; its total phi cost over
        the greedy is no larger than phi's on this data (cascades could in
        principle break this; it holds here and is a sanity check, not a law)."""
        cat, val = anchors
        dx, dy = 0.5, 0.6
        ref = layout(
            cat, val, dx, dy, phi=PHI, process_order="spine-drop", one_sided=True, backend="python"
        )
        got = layout(
            cat,
            val,
            dx,
            dy,
            phi=PHI,
            process_order="spine-drop",
            one_sided=True,
            gravity=Gravity(0.0),
        )
        assert _min_dist(got[0] / dx, got[1] / dy) >= 1.0 - 1e-9

        def total(out):
            return float(np.sum(((out[0] - cat) / dx) ** 2 + PHI * ((out[1] - val) / dy) ** 2))

        assert total(got) <= total(ref) * (1 + 1e-9)


class TestGravitySanity:
    @pytest.mark.parametrize("g", [0.5, 2.0, 10.0])
    @pytest.mark.parametrize("order", ["ascending", "spine-drop"])
    def test_never_overlap(self, anchors, g, order):
        cat, val = anchors
        dx, dy = 0.5, 0.6
        out = layout(
            cat, val, dx, dy, phi=PHI, process_order=order, one_sided=True, gravity=Gravity(g)
        )
        assert out is not None
        assert _min_dist(out[0] / dx, out[1] / dy) >= 1.0 - 1e-9

    def test_gate_sparse_plot_untouched(self):
        cat = np.zeros(6)
        val = np.arange(6.0) * 3.0  # three diameters apart: every anchor is feasible
        out = layout(cat, val, 1.0, 1.0, phi=PHI, gravity=Gravity(5.0))
        assert np.array_equal(out[0], cat) and np.array_equal(out[1], val)

    @pytest.mark.parametrize("g", [0.5, 3.0])
    def test_winner_inside_window(self, anchors, g):
        cat, val = anchors
        grav = Gravity(g)
        checked = 0
        for ai, bi, PA, PB in _placed_sets(cat, val, one_sided=True, val_bounds=None):
            ref = _gravity_reference(ai, bi, PA, PB, PHI, grav, one_sided=True)
            res = _gravity_best(ai, bi, PA, PB, PHI, grav, one_sided=True, val_bounds=None)
            if ref is None or res is None or (res[0] == ai and res[1] == bi):
                continue
            _, _, delta, Delta, _ = ref
            assert abs(res[0] - ai) <= Delta + 1e-9
            assert abs(res[1] - bi) <= delta + 1e-9
            checked += 1
        assert checked > 5

    def test_growth_term_is_monotone_in_g(self, anchors):
        """beta = 0: with only the growth term, the chosen |offset| never
        increases with g (per placement, fixed neighbours), up to the grid."""
        cat, val = anchors
        sets = _placed_sets(cat, val, one_sided=True, val_bounds=None)
        violations = 0
        for ai, bi, PA, PB in sets[10:24]:
            prev = None
            for g in (0.0, 1.0, 5.0, 25.0):
                grav = Gravity(g, beta=0.0, h=0.1)
                res = _gravity_best(ai, bi, PA, PB, PHI, grav, one_sided=True, val_bounds=None)
                d = abs(res[0] - ai)
                if prev is not None and d > prev + 0.1 + 1e-9:
                    violations += 1
                prev = d
        assert violations == 0

    def test_refining_the_grid_never_finds_a_worse_cost(self, anchors):
        cat, val = anchors
        sets = _placed_sets(cat, val, one_sided=True, val_bounds=None)
        worse = 0
        for ai, bi, PA, PB in sets[10:30]:
            coarse = _gravity_best(
                ai, bi, PA, PB, PHI, Gravity(2.0, h=0.2), one_sided=True, val_bounds=None
            )
            fine = _gravity_best(
                ai, bi, PA, PB, PHI, Gravity(2.0, h=0.1), one_sided=True, val_bounds=None
            )
            if fine[2] > coarse[2] + 1e-9:
                worse += 1
        assert worse == 0


class TestGravityValidation:
    def test_requires_phi_and_circles(self, anchors):
        cat, val = anchors
        with pytest.raises(ValueError, match="pass phi"):
            layout(cat, val, 0.5, 0.6, gravity=Gravity(1.0))
        with pytest.raises(TypeError, match="Gravity instance"):
            layout(cat, val, 0.5, 0.6, phi=PHI, gravity={"g": 1.0})
        sq = PolygonShape(np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]))
        with pytest.raises(NotImplementedError, match="circles only"):
            layout(cat, val, 0.5, 0.6, phi=PHI, gravity=Gravity(1.0), shape=sq)

    def test_c_backend_matches_python(self, anchors):
        cat, val = anchors
        from idd_figures.beeswarm_core import has_fast_backend

        if not has_fast_backend():
            pytest.skip("kernel not built")
        c = layout(cat, val, 0.5, 0.6, phi=PHI, gravity=Gravity(1.0), backend="c")
        py = layout(cat, val, 0.5, 0.6, phi=PHI, gravity=Gravity(1.0), backend="python")
        assert np.allclose(c[0], py[0], atol=1e-9) and np.allclose(c[1], py[1], atol=1e-9)

    def test_wrapper_threads_gravity(self):
        mpl = pytest.importorskip("matplotlib")
        mpl.use("Agg")
        import matplotlib.pyplot as plt

        from idd_figures.idd_beeswarm import position_all_points

        rng = np.random.default_rng(3)
        x = np.zeros(40)
        y = rng.normal(size=40)
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.set_xlim(y.min() - 0.5, y.max() + 0.5)
        ax.set_ylim(-0.2, 1.5)
        res, extent = position_all_points(
            x,
            y,
            60.0,
            0.1,
            fig,
            ax,
            orient="h",
            one_sided=True,
            process_order="spine-drop",
            phi=PHI,
            gravity=Gravity(1.0),
        )
        plt.close(fig)
        assert res is not None and np.isfinite(extent)
