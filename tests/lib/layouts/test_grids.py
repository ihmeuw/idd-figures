"""Unit tests for the GridSpec layout engine (panel_grid / facet_grid)."""

import matplotlib.pyplot as plt
import pytest

from idd_figures.lib import example_data as ed
from idd_figures.lib.layouts.grids import cell, colorbar, facet_grid, grid, paint, panel_grid
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


def test_panel_grid_attaches_named_axes_registry():
    df = _ts()
    spec = grid((1, 1), [
        cell((0, 0), paint(lines_panel, df, x="year_id", value="value", hue="series"), name="only"),
    ])
    fig = panel_grid(spec, figsize=(4, 3))
    assert fig.axes_by_name["only"] is fig.axes[0]
    plt.close(fig)


def test_nested_grid_margins_raise():
    df = _ts()
    inner = grid((1, 1), [
        cell((0, 0), paint(lines_panel, df, x="year_id", value="value", hue="series")),
    ], margins={"left": 0.2})
    spec = grid((1, 1), [cell((0, 0), inner)])
    with pytest.raises(ValueError, match="margin"):
        panel_grid(spec, figsize=(4, 3))


def test_colorbar_cell_draws_the_ramp():
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    df = _ts()
    sm = ScalarMappable(norm=Normalize(0, 1), cmap="viridis")
    spec = grid((2, 1), [
        cell((0, 0), paint(lines_panel, df, x="year_id", value="value", hue="series")),
        cell((1, 0), colorbar(sm, orientation="horizontal"), name="cbar"),
    ], height_ratios=[0.9, 0.1])
    fig = panel_grid(spec, figsize=(5, 4))
    cax = fig.axes_by_name["cbar"]
    assert len(cax.collections) + len(cax.images) > 0  # the ramp was actually drawn
    plt.close(fig)


def test_colorbar_cell_spans_panel_columns():
    # forecast-mbp pattern: two panels over ONE shared horizontal bar spanning both
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    df = _ts()
    sm = ScalarMappable(norm=Normalize(0, 1), cmap="viridis")
    spec = grid((2, 2), [
        cell((0, 0), paint(lines_panel, df, x="year_id", value="value", hue="series"), name="a"),
        cell((0, 1), paint(lines_panel, df, x="year_id", value="value", hue="series"), name="b"),
        cell((1, slice(0, 2)), colorbar(sm, orientation="horizontal"), name="bar"),
    ], height_ratios=[0.92, 0.08])
    fig = panel_grid(spec, figsize=(8, 5))
    bar = fig.axes_by_name["bar"].get_position(original=True)
    a = fig.axes_by_name["a"].get_position(original=True)
    b = fig.axes_by_name["b"].get_position(original=True)
    assert bar.x0 <= a.x0 + 1e-9  # footprint = the union of the served panels
    assert bar.x1 >= b.x1 - 1e-9
    plt.close(fig)


def test_facet_grid_projection_makes_projected_axes():
    pdat = ed.make_forecast_panel_df()
    sub = pdat[(pdat["measure"] == "mort") & (pdat["metric"] == "rate")]

    def dot(ax, df, **_):
        ax.plot([0, 1], [0, 1])

    fig = facet_grid(sub, dot, col="group", ncol=3, projection="polar")
    assert all(ax.name == "polar" for ax in fig.axes)
    plt.close(fig)


def test_facet_grid_projection_refuses_axis_sharing():
    pdat = ed.make_forecast_panel_df()
    sub = pdat[(pdat["measure"] == "mort") & (pdat["metric"] == "rate")]
    with pytest.raises(ValueError, match="sharex/sharey"):
        facet_grid(sub, lambda ax, df: None, col="group", projection="polar", sharex=True)
