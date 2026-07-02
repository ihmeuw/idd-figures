"""Unit tests for idd_figures.lib.colors."""

import pytest
from matplotlib.colors import BoundaryNorm, ListedColormap

from idd_figures.lib.colors import (
    binned_colormap,
    diverging_colors,
    get_colors,
    signed_diverging_cmap,
)


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
