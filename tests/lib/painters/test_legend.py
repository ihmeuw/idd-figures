"""Unit tests for the general bin-legend painter."""

import matplotlib.pyplot as plt

from idd_figures.lib.bins import map_bin_labels
from idd_figures.lib.colors import binned_colormap
from idd_figures.lib.painters.legend import bin_legend_panel


def test_discrete_legend_draws_one_patch_per_bin():
    _, _, colors = binned_colormap([0, 25, 50, 75, 100])
    labels = map_bin_labels([0, 25, 50, 75, 100])
    fig, ax = plt.subplots()
    out = bin_legend_panel(ax, colors=colors, labels=labels)
    assert out is ax
    assert len(ax.patches) == 4
    assert not ax.axison
    plt.close(fig)


def test_colorbar_mode_needs_mappable():
    fig, ax = plt.subplots()
    cmap, norm, _ = binned_colormap([0, 1, 2, 3])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    out = bin_legend_panel(ax, mappable=sm, use_colorbar=True)
    assert out is ax
    plt.close(fig)


def test_colorbar_mode_shows_numeric_ticks():
    from matplotlib.colors import Normalize

    fig, ax = plt.subplots()
    sm = plt.cm.ScalarMappable(norm=Normalize(0, 100))
    sm.set_array([])
    bin_legend_panel(ax, mappable=sm, use_colorbar=True, orientation="horizontal")
    cax = ax.child_axes[0]  # colorbar is drawn on an inset (matches the swatch rectangle)
    labels = [t.get_text() for t in cax.get_xticklabels() if t.get_text()]
    assert len(labels) > 0
    plt.close(fig)


def test_colorbar_label_lands_on_the_inset():
    from matplotlib.colors import Normalize

    fig, ax = plt.subplots()
    sm = plt.cm.ScalarMappable(norm=Normalize(0, 100))
    sm.set_array([])
    bin_legend_panel(ax, mappable=sm, use_colorbar=True, orientation="horizontal", cbar_label="HDI")
    cax = ax.child_axes[0]
    assert cax.get_xlabel() == "HDI"  # horizontal bar labels along x
    plt.close(fig)


def test_colorbar_ticks_pin_positions_and_labels():
    import numpy as np
    from matplotlib.colors import Normalize

    fig, ax = plt.subplots()
    sm = plt.cm.ScalarMappable(norm=Normalize(0, 100))
    sm.set_array([])
    ticks = [0, 25, 50, 100]
    bin_legend_panel(ax, mappable=sm, use_colorbar=True, ticks=ticks, labels=["a", "b", "c", "d"])
    cax = ax.child_axes[0]
    assert np.allclose(cax.get_xticks(), ticks)  # positions are the declared values
    assert [t.get_text() for t in cax.get_xticklabels()] == ["a", "b", "c", "d"]
    plt.close(fig)


def test_discrete_mode_rejects_ticks():
    import pytest

    _, _, colors = binned_colormap([0, 50, 100])
    fig, ax = plt.subplots()
    with pytest.raises(ValueError, match="colorbar mode"):
        bin_legend_panel(ax, colors=colors, ticks=[0, 50, 100])
    plt.close(fig)


def test_colorbar_inset_fills_swatch_rectangle():
    # continuous ramp should occupy the same band as discrete swatches: bin_bottom..bin_top
    from matplotlib.colors import Normalize

    fig, ax = plt.subplots()
    sm = plt.cm.ScalarMappable(norm=Normalize(0, 100))
    sm.set_array([])
    bin_legend_panel(ax, mappable=sm, use_colorbar=True, bin_bottom=0.45, bin_top=0.85, margin=0.05)
    axp, cp = ax.get_position(), ax.child_axes[0].get_position()
    h_frac = cp.height / axp.height
    y0_frac = (cp.y0 - axp.y0) / axp.height
    assert abs(h_frac - (0.85 - 0.45)) < 0.02  # band height == bin_top - bin_bottom
    assert abs(y0_frac - 0.45) < 0.02  # band bottom == bin_bottom
    plt.close(fig)
