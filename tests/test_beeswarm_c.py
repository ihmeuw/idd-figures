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
        with pytest.raises(NotImplementedError, match="backend='c'"):
            layout(cat, val, 0.4, 0.5, shape=square, backend="c")
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
