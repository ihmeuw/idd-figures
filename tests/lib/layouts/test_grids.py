"""Unit tests for the GridSpec layout engine (panel_grid / facet_grid)."""

import matplotlib.pyplot as plt

from idd_figures.lib import example_data as ed
from idd_figures.lib.layouts.grids import cell, facet_grid, grid, paint, panel_grid
from idd_figures.lib.painters.lines import lines_panel


def _ts():
    return ed.make_timeseries_df(n_series=2)


def test_panel_grid_creates_one_axes_per_paint_cell():
    df = _ts()
    spec = grid(
        (1, 2),
        [
            cell((0, 0), paint(lines_panel, df, x="year_id", value="value", hue="series")),
            cell((0, 1), paint(lines_panel, df, x="year_id", value="value", hue="series")),
        ],
    )
    fig = panel_grid(spec, figsize=(8, 4))
    assert len(fig.axes) == 2
    plt.close(fig)


def test_facet_grid_axes_count_matches_facets():
    pdat = ed.make_forecast_panel_df()
    sub = pdat[(pdat["measure"] == "mort") & (pdat["metric"] == "rate")]
    n = sub["group"].nunique()
    fig = facet_grid(sub, lines_panel, col="group", ncol=3,
                     panel_kwargs={"x": "year_id", "value": "mid", "hue": "series"})
    assert len(fig.axes) == n
    plt.close(fig)


def test_facet_grid_sharey_links_limits():
    pdat = ed.make_forecast_panel_df()
    sub = pdat[(pdat["measure"] == "mort") & (pdat["metric"] == "rate")]
    fig = facet_grid(sub, lines_panel, col="group", ncol=3, sharey=True,
                     panel_kwargs={"x": "year_id", "value": "mid", "hue": "series"})
    axes = fig.axes
    assert axes[0].get_ylim() == axes[1].get_ylim()
    plt.close(fig)


def test_nested_grid_runs():
    from idd_figures.lib.examples import exemplar_nested_grid

    fig = exemplar_nested_grid()
    assert len(fig.axes) >= 8  # 8 line panels + gutter labels + legend
    plt.close(fig)
