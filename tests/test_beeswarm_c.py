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
