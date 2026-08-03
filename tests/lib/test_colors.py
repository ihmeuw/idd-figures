"""Unit tests for idd_figures.lib.colors."""

import pytest
from matplotlib.colors import BoundaryNorm, ListedColormap

from idd_figures.lib.colors import (
    binned_colormap,
    clipped_diverging_cmap,
    diverging_colors,
    get_colors,
    signed_diverging_cmap,
)


def test_clipped_diverging_removes_the_middle_band():
    cmap = clipped_diverging_cmap()  # default: cut the middle 25% of 256 samples
    assert isinstance(cmap, ListedColormap)
    assert cmap.N == 192
    lo_side, hi_side = cmap(0.49), cmap(0.51)  # hard seam: neighbours differ sharply
    assert abs(lo_side[0] - hi_side[0]) + abs(lo_side[2] - hi_side[2]) > 0.2


def test_clipped_diverging_rejects_off_centre_cuts():
    with pytest.raises(ValueError, match="symmetric"):
        clipped_diverging_cmap(lo=0.30, hi=0.60)


def test_get_colors_count():
    assert len(get_colors(5)) == 5


def test_get_colors_rgba():
    assert all(len(c) == 4 for c in get_colors(3))


def test_get_colors_below_two_raises():
    with pytest.raises(ValueError, match="n_bins"):
        get_colors(1)


def test_diverging_len():
    assert len(diverging_colors(4)) == 4


def test_signed_cmap_jumps():
    cmap = signed_diverging_cmap()
    assert cmap(0.0) != cmap(1.0)


def test_binned_returns_cmap_norm_colors():
    cmap, norm, cols = binned_colormap([0, 1, 2, 3])
    assert isinstance(cmap, ListedColormap)
    assert isinstance(norm, BoundaryNorm)
    assert len(cols) == 3


def test_binned_force_white_zero():
    _, _, cols = binned_colormap([0, 1, 2, 3], force_white_zero=True)
    assert cols[0] == (1.0, 1.0, 1.0, 1.0)


def test_binned_diverging_white_middle():
    _, _, cols = binned_colormap([0, 1, 2, 3, 4, 5], diverging=True, force_white_zero=True)
    assert cols[2] == (1.0, 1.0, 1.0, 1.0)


def test_binned_diverging_remove_middle_keeps_n_colors():
    # n = 4 bins; remove_middle drops the central diverging pair but still yields n colours
    _, _, cols = binned_colormap([-2, -1, 0, 1, 2], diverging=True, remove_middle=True)
    assert len(cols) == 4


def test_remove_middle_even_symmetric_per_side():
    # even n=4: sample 6, drop the seam-straddling pair -> exactly 2 per side
    wide = diverging_colors(6)
    _, _, cols = binned_colormap([-2, -1, 0, 1, 2], diverging=True, remove_middle=True)
    assert cols == wide[:2] + wide[4:]


def test_remove_middle_odd_white_centre_symmetric_per_side():
    # odd n=5: white centre bin + one colour dropped from EACH side -> 2 / white / 2
    wide = diverging_colors(6)
    _, _, cols = binned_colormap([-2, -1, 0, 1, 2, 3], diverging=True, remove_middle=True)
    assert len(cols) == 5
    assert cols[2] == (1.0, 1.0, 1.0, 1.0)
    assert cols[:2] == wide[:2]
    assert cols[3:] == wide[4:]


def test_remove_middle_even_with_white_zero_raises():
    with pytest.raises(ValueError, match="centre bin"):
        binned_colormap(
            [-2, -1, 0, 1, 2], diverging=True, remove_middle=True, force_white_zero=True
        )
