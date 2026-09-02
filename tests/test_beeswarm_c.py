"""Parity of the C99 kernel with the Python engines (extraction step 4).
Skipped when no C compiler is available."""

import shutil

import numpy as np
import pytest

from idd_figures.beeswarm_core import CIRCLE, _layout_phi, _layout_swarm, _processing_order

pytestmark = pytest.mark.skipif(shutil.which("gcc") is None, reason="no gcc")


@pytest.fixture(scope="module")
def C():
    from idd_figures import beeswarm_c

    beeswarm_c.lib()
    return beeswarm_c


@pytest.fixture
def anchors():
    rng = np.random.default_rng(9)
    cat = rng.integers(0, 3, 120).astype(float) * 40.0
    val = rng.normal(size=120) * 6.0
    return cat, val


@pytest.mark.parametrize("order_name", ["ascending", "middle-out", "descending"])
@pytest.mark.parametrize("one_sided", [False, True])
def test_swarm_matches_python(C, anchors, order_name, one_sided):
    cat, val = anchors
    order = _processing_order(cat, val, order_name)
    py = _layout_swarm(cat, val, order, CIRCLE, one_sided)
    c = C.layout_swarm(cat, val, order, one_sided)
    assert np.allclose(py, c, rtol=0, atol=1e-9)


@pytest.mark.parametrize("phi", [0.5, 3.0, 1e6])
@pytest.mark.parametrize("one_sided", [False, True])
@pytest.mark.parametrize("bounded", [False, True])
def test_phi_matches_python(C, anchors, phi, one_sided, bounded):
    cat, val = anchors
    order = _processing_order(cat, val, "ascending")
    vb = (val.min() + 0.5, val.max() - 0.5) if bounded else None
    py = _layout_phi(cat, val, order, 1.0, phi, one_sided, vb)
    c = C.layout_phi(cat, val, order, phi, one_sided, vb)
    assert np.allclose(py[0], c[0], rtol=0, atol=1e-7)
    assert np.allclose(py[1], c[1], rtol=0, atol=1e-7)


def test_tie_break_matches(C):
    a = C.layout_swarm(np.zeros(3), np.zeros(3), np.arange(3), one_sided=False)
    assert np.allclose(a, [0.0, 1.0, -1.0])


def test_input_validation(C):
    with pytest.raises(ValueError, match="same length"):
        C.layout_swarm(np.zeros(3), np.zeros(2), np.arange(3))


class TestDispatchWithKernel:
    def test_kernel_reported_available(self, C):
        from idd_figures.beeswarm_core import has_fast_backend

        assert C.available()
        assert has_fast_backend()

    def test_c_backend_equals_python_through_layout(self, C, anchors):
        from idd_figures.beeswarm_core import layout

        cat, val = anchors
        for kw in ({}, {"phi": 2.0}, {"process_order": "middle-out", "phi": 0.7}):
            c = layout(cat, val, 0.4, 0.5, one_sided=True, backend="c", **kw)
            py = layout(cat, val, 0.4, 0.5, one_sided=True, backend="python", **kw)
            assert np.allclose(c[0], py[0], atol=1e-7) and np.allclose(c[1], py[1], atol=1e-7)

    def test_c_backend_refuses_unported_configurations(self, C, anchors):
        from idd_figures.beeswarm_core import layout
        from idd_figures.beeswarm_shapes import PolygonShape

        cat, val = anchors
        square = PolygonShape(np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]))
        with pytest.raises(NotImplementedError, match="circles only"):
            layout(cat, val, 0.4, 0.5, shape=square, phi=1.0, backend="c")
        with pytest.raises(NotImplementedError, match="backend='c'"):
            layout(cat, val, 0.4, 0.5, method="hex", backend="c")


@pytest.mark.parametrize("phi", [None, 0.7, 3.0])
@pytest.mark.parametrize("one_sided", [False, True])
@pytest.mark.parametrize("bin_order", ["middle-out", "ascending", "descending"])
def test_spine_drop_matches_python(C, anchors, phi, one_sided, bin_order):
    from idd_figures.beeswarm_core import _spine_drop_layout

    cat, val = anchors
    vb = (val.min() + 0.5, val.max() - 0.5) if phi else None
    py = _spine_drop_layout(
        cat, cat.copy(), val, phi=phi, one_sided=one_sided, val_bounds=vb, bin_order=bin_order
    )
    c = C.spine_drop(
        cat, cat.copy(), val, phi=phi, one_sided=one_sided, val_bounds=vb, bin_order=bin_order
    )
    assert (py is None) == (c is None)
    tol = 1e-9 if phi is None else 1e-7
    assert np.allclose(py[0], c[0], rtol=0, atol=tol)
    assert np.allclose(py[1], c[1], rtol=0, atol=tol)


def test_spine_drop_through_layout_dispatch(C, anchors):
    from idd_figures.beeswarm_core import layout

    cat, val = anchors
    for kw in ({}, {"phi": 1.0}):
        c = layout(cat, val, 0.4, 0.5, process_order="spine-drop", backend="c", **kw)
        py = layout(cat, val, 0.4, 0.5, process_order="spine-drop", backend="python", **kw)
        assert np.allclose(c[0], py[0], atol=1e-7) and np.allclose(c[1], py[1], atol=1e-7)


def test_spine_drop_validation(C):
    with pytest.raises(ValueError, match="bin_order"):
        C.spine_drop(np.zeros(3), np.zeros(3), np.arange(3.0), bin_order="sideways")
    with pytest.raises(ValueError, match="same length"):
        C.spine_drop(np.zeros(2), np.zeros(3), np.arange(3.0))


def _regular(k, r=0.5, rot=0.0):
    th = rot + 2 * np.pi * np.arange(k) / k
    return np.column_stack([r * np.cos(th), r * np.sin(th)])


def _star(k=5, r_out=0.5, r_in=0.2):
    th = np.pi / 2 + np.pi * np.arange(2 * k) / k
    r = np.where(np.arange(2 * k) % 2 == 0, r_out, r_in)
    return np.column_stack([r * np.cos(th), r * np.sin(th)])


def _shapes():
    from idd_figures.beeswarm_shapes import PolygonShape

    return {
        "square": PolygonShape(_regular(4, np.sqrt(0.5), np.pi / 4)),
        "triangle": PolygonShape(_regular(3)),
        "hexagon": PolygonShape(_regular(6)),
        "star-hull": PolygonShape(_star(), mode="hull"),
        "star-decompose": PolygonShape(_star(), mode="decompose"),
    }


@pytest.fixture
def dense_anchors():
    rng = np.random.default_rng(13)
    cat = rng.integers(0, 3, 150).astype(float) * 30.0
    val = rng.normal(size=150) * 5.0
    return cat, val


@pytest.mark.parametrize("name", ["square", "triangle", "hexagon", "star-hull", "star-decompose"])
@pytest.mark.parametrize("order_name", ["ascending", "middle-out", "spine"])
@pytest.mark.parametrize("one_sided", [False, True])
def test_polygon_swarm_matches_python(C, dense_anchors, name, order_name, one_sided):
    from idd_figures.beeswarm_core import _layout_swarm, _processing_order, _spine_bin_order

    cat, val = dense_anchors
    shape = _shapes()[name]
    if order_name == "spine":
        order = _spine_bin_order(cat, val, shape.stack_height)
    else:
        order = _processing_order(cat, val, order_name)
    py = _layout_swarm(cat, val, order, shape, one_sided)
    c = C.layout_swarm(cat, val, order, one_sided=one_sided, shape=shape)
    assert np.array_equal(py, c), np.abs(py - c).max()


@pytest.mark.parametrize("name", ["square", "star-hull", "star-decompose"])
@pytest.mark.parametrize("one_sided", [False, True])
@pytest.mark.parametrize("bin_order", ["middle-out", "ascending", "descending"])
def test_polygon_spine_drop_matches_python(C, dense_anchors, name, one_sided, bin_order):
    from idd_figures.beeswarm_core import _spine_drop_layout

    cat, val = dense_anchors
    shape = _shapes()[name]
    py = _spine_drop_layout(
        cat, cat.copy(), val, shape=shape, one_sided=one_sided, bin_order=bin_order
    )
    c = C.spine_drop(cat, cat.copy(), val, one_sided=one_sided, bin_order=bin_order, shape=shape)
    assert (py is None) == (c is None)
    assert np.array_equal(py[0], c[0]) and np.array_equal(py[1], c[1])


def test_polygon_through_layout_dispatch(C, dense_anchors):
    from idd_figures.beeswarm_core import layout

    cat, val = dense_anchors
    star = _shapes()["star-decompose"]
    for kw in ({}, {"process_order": "spine-drop"}, {"process_order": "spine"}):
        c = layout(cat, val, 0.4, 0.5, shape=star, backend="c", **kw)
        py = layout(cat, val, 0.4, 0.5, shape=star, backend="python", **kw)
        assert np.array_equal(c[0], py[0]) and np.array_equal(c[1], py[1])


def test_polygon_phi_refused_in_c(C):
    with pytest.raises(NotImplementedError, match="circles only"):
        C.spine_drop(np.zeros(3), np.zeros(3), np.arange(3.0), phi=1.0, shape=_shapes()["square"])


# ---------------------------------------------------------------- gravity: two gates
GPHI = 2.0


def _phi_placed_sets(cat, val, one_sided, val_bounds, n_steps=40):
    from idd_figures.beeswarm_core import _phi_best

    order = _processing_order(cat, val, "ascending")
    PA, PB = np.empty(cat.size), np.empty(cat.size)
    out = []
    for k, i in enumerate(order[:n_steps]):
        out.append((cat[i], val[i], PA[:k].copy(), PB[:k].copy()))
        res = _phi_best(cat[i], val[i], PA[:k], PB[:k], 1.0, GPHI, one_sided, val_bounds)
        PA[k], PB[k] = res[0], res[1]
    return out


@pytest.fixture
def grav_anchors():
    rng = np.random.default_rng(17)
    cat = rng.integers(0, 2, 70).astype(float) * 30.0
    val = rng.normal(size=70) * 3.0
    return cat, val


class TestGravityGateAnalytic:
    """Gate 2 (free): C gravity in analytic mode at g = 0 IS the kernel's own
    phi step, bit for bit (the shared machinery survived the port), and sits
    within the standing 1e-7 cross-language phi tolerance of Python's phi
    (the ellipse solve is not bit-identical across numpy and libm; it never
    was, see the phi gate above)."""

    @pytest.mark.parametrize("one_sided", [False, True])
    @pytest.mark.parametrize("bounded", [False, True])
    def test_step_is_kernel_phi_best_bit_for_bit(self, C, grav_anchors, one_sided, bounded):
        from idd_figures.beeswarm_core import Gravity, _phi_best

        cat, val = grav_anchors
        vb = (val.min() - 0.2, val.max() + 0.2) if bounded else None
        grav = Gravity(0.0, exhaustive=False)
        for ai, bi, PA, PB in _phi_placed_sets(cat, val, one_sided, vb):
            pc = C.phi_best(ai, bi, PA, PB, GPHI, one_sided=one_sided, val_bounds=vb)
            q = C.gravity_best(ai, bi, PA, PB, GPHI, grav, one_sided=one_sided, val_bounds=vb)
            assert tuple(map(float, pc)) == tuple(map(float, q))
            ppy = _phi_best(ai, bi, PA, PB, 1.0, GPHI, one_sided, vb)
            assert np.allclose(ppy, q, rtol=0, atol=1e-7)

    @pytest.mark.parametrize("order_name", ["ascending", "middle-out"])
    @pytest.mark.parametrize("one_sided", [False, True])
    def test_layout_is_kernel_phi_layout(self, C, grav_anchors, order_name, one_sided):
        from idd_figures.beeswarm_core import Gravity, _layout_phi

        cat, val = grav_anchors
        order = _processing_order(cat, val, order_name)
        pc = C.layout_phi(cat, val, order, GPHI, one_sided=one_sided)
        q = C.layout_gravity(
            cat, val, order, GPHI, Gravity(0.0, exhaustive=False), one_sided=one_sided
        )
        assert np.array_equal(pc[0], q[0]) and np.array_equal(pc[1], q[1])
        py = _layout_phi(cat, val, order, 1.0, GPHI, one_sided, None)
        assert np.allclose(py[0], q[0], rtol=0, atol=1e-7) and np.allclose(
            py[1], q[1], rtol=0, atol=1e-7
        )

    def test_spine_drop_is_kernel_phi_drop(self, C, grav_anchors):
        from idd_figures.beeswarm_core import Gravity

        cat, val = grav_anchors
        pc = C.spine_drop(cat, cat.copy(), val, phi=GPHI, one_sided=True)
        q = C.spine_drop(
            cat, cat.copy(), val, phi=GPHI, one_sided=True, gravity=Gravity(0.0, exhaustive=False)
        )
        assert np.array_equal(pc[0], q[0]) and np.array_equal(pc[1], q[1])


class TestGravityGateExhaustive:
    """Gate 1 (the real one): C gravity vs Python gravity, both exhaustive, 1e-9."""

    @pytest.mark.parametrize("g", [0.0, 0.7, 3.0])
    @pytest.mark.parametrize("one_sided", [False, True])
    @pytest.mark.parametrize("bounded", [False, True])
    def test_step_matches_python(self, C, grav_anchors, g, one_sided, bounded):
        from idd_figures.beeswarm_core import Gravity, _gravity_best

        cat, val = grav_anchors
        vb = (val.min() - 0.2, val.max() + 0.2) if bounded else None
        grav = Gravity(g)
        for ai, bi, PA, PB in _phi_placed_sets(cat, val, one_sided, vb, n_steps=30):
            p = _gravity_best(ai, bi, PA, PB, GPHI, grav, one_sided, vb)
            q = C.gravity_best(ai, bi, PA, PB, GPHI, grav, one_sided=one_sided, val_bounds=vb)
            assert np.allclose(p, q, rtol=0, atol=1e-9), (p, q)

    @pytest.mark.parametrize("g", [0.0, 1.0])
    @pytest.mark.parametrize("order_name", ["ascending", "spine-drop"])
    @pytest.mark.parametrize("one_sided", [False, True])
    def test_layout_matches_python(self, C, grav_anchors, g, order_name, one_sided):
        from idd_figures.beeswarm_core import Gravity, layout

        cat, val = grav_anchors
        kw = {
            "phi": GPHI,
            "gravity": Gravity(g),
            "process_order": order_name,
            "one_sided": one_sided,
        }
        py = layout(cat, val, 0.5, 0.6, backend="python", **kw)
        c = layout(cat, val, 0.5, 0.6, backend="c", **kw)
        assert np.allclose(py[0], c[0], rtol=0, atol=1e-9)
        assert np.allclose(py[1], c[1], rtol=0, atol=1e-9)

    def test_gravity_tolerance_does_not_leak(self, C, anchors):
        """The other engines keep their exact gates: re-assert one here."""
        cat, val = anchors
        order = _processing_order(cat, val, "ascending")
        py = _layout_swarm(cat, val, order, CIRCLE, one_sided=True)
        c = C.layout_swarm(cat, val, order, one_sided=True)
        assert np.array_equal(py, c)
