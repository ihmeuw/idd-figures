"""Unit tests for the figure-anatomy overlay."""

import matplotlib.pyplot as plt

from idd_figures.lib import example_data as ed
from idd_figures.lib.layouts.anatomy import show_anatomy
from idd_figures.lib.painters.lines import lines_panel


def _rects(fig):
    return [a for a in fig.artists if a.__class__.__name__ == "Rectangle"]


def test_show_anatomy_boxes_single_panel():
    df = ed.make_timeseries_df(n_series=2)
    fig, ax = plt.subplots(figsize=(8, 5))
    lines_panel(ax, df, x="year_id", value="value", hue="series", xlabel="year", ylabel="value")
    ax.set_title("t")
    out = show_anatomy(fig)
    assert out is fig
    # outer + panel + xlabel + ylabel + title + xticks + yticks
    assert len(_rects(fig)) >= 6
    plt.close(fig)


def test_show_anatomy_on_grid_runs():
    from idd_figures.lib import examples as ex

    fig = ex.exemplar_forecast_superregion_facet()
    show_anatomy(fig)
    assert len(_rects(fig)) >= len(fig.axes)  # at least one panel box per axes
    plt.close(fig)
