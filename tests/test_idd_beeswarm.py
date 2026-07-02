"""Unit tests for idd_figures.idd_beeswarm geometry helpers.

These cover the display-coordinate distance/overlap primitives the beeswarm
solver is built on. A headless Agg figure provides a real transData so the
pixel<->data conversions are exercised end to end. The full binary-search
solver (find_optimal_s / position_all_points) is not yet covered — see
.claude/DECISIONS.md.
"""

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from idd_figures.idd_beeswarm import check_overlap, estimate_distance_data_units


@pytest.fixture
def fig_ax():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    fig.canvas.draw()
    yield fig, ax
    plt.close(fig)


def _radius_pixels(s, fig):
    return (np.sqrt(s) / 2) * (fig.dpi / 72)


class TestEstimateDistance:
    def test_coincident_points_are_negative_one_diameter(self, fig_ax):
        fig, ax = fig_ax
        d = estimate_distance_data_units((1, 1), (1, 1), s=100, fig=fig, ax=ax)
        assert d == pytest.approx(-2 * _radius_pixels(100, fig))

    def test_distance_grows_with_separation(self, fig_ax):
        fig, ax = fig_ax
        near = estimate_distance_data_units((1, 1), (2, 1), s=100, fig=fig, ax=ax)
        far = estimate_distance_data_units((1, 1), (5, 1), s=100, fig=fig, ax=ax)
        assert far > near


class TestCheckOverlap:
    def test_coincident_points_overlap(self, fig_ax):
        fig, ax = fig_ax
        # check_overlap returns a numpy bool, so assert on truthiness, not identity.
        assert check_overlap((1, 1), (1, 1), s=100, gap_fraction=0.1, fig=fig, ax=ax)

    def test_far_points_do_not_overlap(self, fig_ax):
        fig, ax = fig_ax
        assert not check_overlap((1, 1), (9, 9), s=100, gap_fraction=0.1, fig=fig, ax=ax)
