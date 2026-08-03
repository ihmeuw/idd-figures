"""Unit tests for the executable anatomy guides.

Smoke depth: each guide must build, carry annotations, and (for the frames
guide) demonstrate its coordinate claim with measurable positions.
"""

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from idd_figures.lib.guides import (
    guide_bar_cell_anatomy,
    guide_coordinate_frames,
    guide_grid_anatomy,
    guide_text_placement,
)


def test_grid_anatomy_annotates_every_margin_and_gap():
    fig = guide_grid_anatomy()
    assert isinstance(fig, Figure)
    text = " ".join(t.get_text() for t in fig.texts)
    for token in ('margins["left"]', 'margins["right"]', 'margins["top"]',
                  'margins["bottom"]', "wspace", "hspace", "height_ratios"):
        assert token in text
    plt.close(fig)


def test_bar_cell_anatomy_measures_the_drawn_swatches():
    fig = guide_bar_cell_anatomy()
    text = " ".join(t.get_text() for t in fig.texts)
    for token in ("margin", "spacing", "bin_bottom", "label_gap"):
        assert token in text
    plt.close(fig)


def test_text_placement_guide_builds_with_anatomy_overlay():
    fig = guide_text_placement()
    assert isinstance(fig, Figure)
    plt.close(fig)


def test_guides_reannotate_with_changed_knobs():
    # the changed-version mechanism: pass different numbers, read them off the figure
    fig = guide_grid_anatomy(wspace=0.8)
    assert any("wspace = 0.8" in t.get_text() for t in fig.texts)
    plt.close(fig)
    fig = guide_bar_cell_anatomy(margin=0.2)
    assert any("margin = 0.2" in t.get_text() for t in fig.texts)
    plt.close(fig)
    fig = guide_text_placement(margins={"left": 0.07, "right": 0.95, "top": 0.86, "bottom": 0.14},
                               notes=False)
    assert any("0.07" in t.get_text() for t in fig.texts)  # margins echoed on the figure
    assert any('margins["bottom"] = 0.14' in t.get_text() for t in fig.texts)  # measured band
    plt.close(fig)


def test_text_styles_guide_labels_every_owner_call():
    from idd_figures.lib.guides import guide_text_styles

    fig = guide_text_styles(xtick_size=6)
    text = " ".join(t.get_text() for t in fig.texts)
    for token in ("set_title", "set_xlabel", "set_ylabel", 'tick_params(axis="x", labelsize=6)',
                  "suptitle", "rc_context"):
        assert token in text
    ax = fig.axes_by_name["p"]
    assert ax.title.get_fontsize() == 20  # default title size actually applied
    assert all(t.get_fontsize() == 6 for t in ax.get_xticklabels())  # override applied
    plt.close(fig)


def test_coordinate_frames_letters_coincide_top_and_diverge_bottom():
    fig = guide_coordinate_frames()
    fig.canvas.draw()

    def letters_in(ax):
        return [t for t in ax.texts if t.get_text() == "A"]

    ax0 = fig.axes_by_name["ax_frame_0"]
    ax1 = fig.axes_by_name["ax_frame_1"]
    assert letters_in(ax0) and letters_in(ax1)  # transAxes letter present in BOTH rows

    # figure-coord letter exists exactly once, coinciding with the top panel corner
    fig_letters = [t for t in fig.texts if t.get_text() == "A"]
    assert len(fig_letters) == 1
    p0 = fig.axes_by_name["fig_frame_0"].get_position(original=True)
    x, y = fig_letters[0].get_position()
    assert abs(x - (p0.x0 + 0.04 * p0.width)) < 1e-9
    assert abs(y - (p0.y0 + 0.92 * p0.height)) < 1e-9
    # ...and that address is NOT the bottom panel's corner (the panels moved)
    p1 = fig.axes_by_name["fig_frame_1"].get_position(original=True)
    assert abs(y - (p1.y0 + 0.92 * p1.height)) > 0.05
    plt.close(fig)


def test_map_guides_build_if_geo_available():
    pytest.importorskip("cartopy")
    pytest.importorskip("geopandas")
    from idd_figures.lib.guides import guide_map_facet_anatomy, guide_map_panel_anatomy

    for fn in (guide_map_panel_anatomy, guide_map_facet_anatomy):
        fig = fn()
        assert isinstance(fig, Figure)
        assert getattr(fig, "_idd_preview", False) or fn is guide_map_panel_anatomy
        plt.close(fig)
