"""Unit tests for idd_figures.lib.style."""

import matplotlib.pyplot as plt
import numpy as np

from idd_figures.lib.style import distinct_colors, ordered_legend, size_by_logpop, turn_off_axes


def test_size_constant_input_is_midpoint():
    out = size_by_logpop([100, 100, 100])
    assert np.allclose(out, (10 + 200) / 2)


def test_size_within_bounds():
    out = size_by_logpop([1, 1000, 1_000_000])
    assert out.min() >= 10 - 1e-9
    assert out.max() <= 200 + 1e-9


def test_distinct_colors_count():
    assert len(distinct_colors(["a", "b", "c"])) == 3


def test_ordered_legend_dedups():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="x")
    ax.plot([0, 1], [1, 2], label="x")
    _, labels = ordered_legend(ax)
    assert labels == ["x"]
    plt.close(fig)


def test_turn_off_single_axes():
    fig, ax = plt.subplots()
    turn_off_axes(ax)
    assert not ax.axison
    plt.close(fig)


def test_turn_off_axes_list():
    fig, axes = plt.subplots(1, 2)
    turn_off_axes(axes)
    assert all(not a.axison for a in axes)
    plt.close(fig)


def test_ui_tick_formatter_rounds():
    from matplotlib.ticker import FuncFormatter

    from idd_figures.lib.style import ui_tick_formatter

    fmt = ui_tick_formatter()
    assert isinstance(fmt, FuncFormatter)
    assert fmt(1234.5, None) == "1230"
