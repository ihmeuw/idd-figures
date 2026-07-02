"""Unit tests for the painters: each draws on a given ax and returns it."""

import matplotlib.pyplot as plt
import pytest

from idd_figures.lib import example_data as ed
from idd_figures.lib.painters.bars import range_bars_panel
from idd_figures.lib.painters.lines import lines_panel
from idd_figures.lib.painters.scatter import scatter_panel
from idd_figures.lib.painters.trajectory import trajectory_panel


def test_lines_draws_and_returns_ax():
    df = ed.make_timeseries_df(n_series=3)
    fig, ax = plt.subplots()
    out = lines_panel(ax, df, x="year_id", value="value", lo="lo", hi="hi", hue="series")
    assert out is ax
    assert len(ax.lines) >= 3
    plt.close(fig)


def test_lines_value_scale_suffix_on_ylabel():
    df = ed.make_timeseries_df(n_series=1)
    fig, ax = plt.subplots()
    lines_panel(ax, df, x="year_id", value="value", ylabel="count",
                value_scale=(1e-3, " (in 1,000s)"))
    assert ax.get_ylabel() == "count (in 1,000s)"
    plt.close(fig)


def test_lines_style_overrides():
    df = ed.make_timeseries_df(n_series=2)
    fig, ax = plt.subplots()
    lines_panel(ax, df, x="year_id", value="value", hue="series",
                lw=3.0, linestyle={"series_0": "--"}, alpha=0.5, marker={"series_0": "o"})
    line0 = ax.lines[0]  # series_0 (sorted hue order)
    assert line0.get_linewidth() == 3.0
    assert line0.get_linestyle() == "--"
    assert line0.get_alpha() == 0.5
    assert line0.get_marker() == "o"
    plt.close(fig)


def test_lines_band_color_override():
    from matplotlib.colors import to_rgba

    df = ed.make_timeseries_df(n_series=1)
    fig, ax = plt.subplots()
    lines_panel(ax, df, x="year_id", value="value", lo="lo", hi="hi",
                band_color="red", band_alpha=0.3)
    facecolor = tuple(ax.collections[0].get_facecolor()[0])
    assert facecolor == pytest.approx(to_rgba("red", 0.3))
    plt.close(fig)


def test_scatter_ref_lines_and_shade():
    df = ed.make_left_behind_df(n=20)
    fig, ax = plt.subplots()
    scatter_panel(ax, df, x="x", y="y", ref_lines={"h": 0, "v": 0},
                  shade={"x": (-0.1, 0), "y": (-0.05, 0), "text": "hi"})
    assert len(ax.collections) >= 1
    assert len(ax.patches) >= 1
    plt.close(fig)


def test_trajectory_draws_path_and_markers():
    df = ed.make_trajectory_df()
    fig, ax = plt.subplots()
    trajectory_panel(ax, df[df["location_id"] == 0], x="level_value", y="aid", order="year_id")
    assert len(ax.lines) >= 1
    assert len(ax.collections) >= 1
    plt.close(fig)


def test_range_bars_draws():
    stats, vals = ed.make_dispersion_stats(n_groups=6)
    fig, ax = plt.subplots()
    range_bars_panel(ax, stats, group_col="A0_location_id", years=(2000, 2023),
                     color_by="super_region_name", values_df=vals)
    assert len(ax.collections) >= 1
    plt.close(fig)


def test_composition_requires_mpltern():
    pytest.importorskip("mpltern")
    from idd_figures.lib.examples import exemplar_composition

    fig = exemplar_composition()
    assert fig is not None
    plt.close(fig)
