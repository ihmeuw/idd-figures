"""Integration smoke tests: every exemplar builds a Figure with axes."""

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from idd_figures.lib import examples as ex


@pytest.mark.parametrize(
    "fn",
    [
        ex.exemplar_lines,
        ex.exemplar_forecast_superregion_facet,
        ex.exemplar_forecast_all_plus_each,
        ex.exemplar_scatter,
        ex.exemplar_left_behind,
        ex.exemplar_trajectory,
        ex.exemplar_range_bars_two_panel,
        ex.exemplar_nested_grid,
    ],
)
def test_exemplar_returns_figure(fn):
    fig = fn()
    assert isinstance(fig, Figure)
    assert len(fig.axes) >= 1
    plt.close(fig)


def test_exemplar_composition_optional():
    pytest.importorskip("mpltern")
    fig = ex.exemplar_composition()
    assert fig is not None
    plt.close(fig)
