"""Unit tests for the layout geometry solvers.

The integration test is the load-bearing one: it builds a REAL gridspec figure
from solved numbers and asserts the realised inch dimensions match the algebra
— i.e. our inversion of matplotlib's mean-cell gap charging is exact.
"""

import matplotlib.pyplot as plt
import pytest

from idd_figures.lib.layouts.geometry import (
    extent_aspect,
    gap_factor,
    map_row_height,
    panel_width,
    solve_figure,
)
from idd_figures.lib.layouts.grids import cell, grid, paint, panel_grid

MARGINS = {"left": 0.05, "right": 0.97, "top": 0.95, "bottom": 0.06}


def test_gap_factor_values():
    assert gap_factor(1, 0.4) == 1.0  # no gaps with one row
    assert gap_factor(2, 0.04) == pytest.approx(1.02)
    assert gap_factor(3, 0.40) == pytest.approx(1 + 2 * 0.4 / 3)


def test_gap_factor_rejects_zero_rows():
    with pytest.raises(ValueError, match="n >= 1"):
        gap_factor(0, 0.1)


def test_extent_aspect():
    assert extent_aspect((0, 6, 0, 4)) == pytest.approx(4 / 6)
    with pytest.raises(ValueError, match="degenerate"):
        extent_aspect((0, 0, 0, 4))


def test_panel_width_single_panel_is_usable_width():
    w = panel_width(10.0, margins=MARGINS, ncols=1, wspace=0.5)  # wspace moot at 1 col
    assert w == pytest.approx(10.0 * (0.97 - 0.05))


def test_panel_width_charges_wspace_against_mean():
    # 3 panels, wspace 0.08: usable = 3*p + 2*0.08*p  ->  p = usable/3.16
    w = panel_width(10.0, margins=MARGINS, ncols=3, wspace=0.08)
    assert w == pytest.approx(10.0 * 0.92 / (3 + 0.08 * 2))


def test_solve_figure_validates():
    with pytest.raises(ValueError, match="positive"):
        solve_figure([1.0, 0.0], margins=MARGINS)


def _empty(ax, _data=None):
    ax.set_xticks([])
    ax.set_yticks([])


def test_solved_grid_realises_exact_inches():
    """End-to-end: nested rows built from solved numbers draw at EXACTLY those inches."""
    fig_w, wspace, hspace, aspect = 10.0, 0.08, 0.25, 0.62
    h_maps3 = map_row_height(fig_w, margins=MARGINS, ncols=3, aspect=aspect, wspace=wspace)
    h_bar = 0.5
    h_map1 = map_row_height(fig_w, margins=MARGINS, ncols=1, aspect=aspect)
    fig_h, ratios = solve_figure([h_maps3, h_bar, h_map1], margins=MARGINS, hspace=hspace)

    row3 = grid(
        (1, 3), [cell((0, j), paint(_empty, None), name=f"p{j}") for j in range(3)], wspace=wspace
    )
    spec = grid(
        (3, 1),
        [
            cell((0, 0), row3),
            cell((1, 0), paint(_empty, None), name="bar"),
            cell((2, 0), paint(_empty, None), name="wide"),
        ],
        height_ratios=ratios,
        margins=MARGINS,
        hspace=hspace,
    )
    fig = panel_grid(spec, figsize=(fig_w, fig_h))

    def inches(name):
        pos = fig.axes_by_name[name].get_position(original=True)
        return pos.width * fig_w, pos.height * fig_h

    for j in range(3):
        w, h = inches(f"p{j}")
        assert w == pytest.approx(
            panel_width(fig_w, margins=MARGINS, ncols=3, wspace=wspace), abs=1e-9
        )
        assert h == pytest.approx(h_maps3, abs=1e-9)
        assert h / w == pytest.approx(aspect, abs=1e-9)  # the fixed-aspect panel FITS its box

    w, h = inches("bar")
    assert h == pytest.approx(h_bar, abs=1e-9)
    w, h = inches("wide")
    assert w == pytest.approx(fig_w * 0.92, abs=1e-9)
    assert h / w == pytest.approx(aspect, abs=1e-9)
    plt.close(fig)
