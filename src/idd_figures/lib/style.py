"""Cross-figure style helpers: marker sizing, category colours, axis utilities.

These are layout/caller-side helpers (sizing, distinct colours, legend de-dup,
blanking axes, tick-label rounding) applied around the painters.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

__all__ = [
    "distinct_colors",
    "ordered_legend",
    "size_by_logpop",
    "turn_off_axes",
    "ui_tick_formatter",
]


def size_by_logpop(values, *, min_size=10.0, max_size=200.0):
    """Scale a (population-like) vector to marker sizes on a log axis, NaN-safe.

    Returns the midpoint size for constant input.
    """
    lp = np.log(np.asarray(values, dtype="float64") + 1.0)
    lo, hi = np.nanmin(lp), np.nanmax(lp)
    if hi == lo:
        return np.full(lp.shape, (min_size + max_size) / 2.0)
    return min_size + (max_size - min_size) * (lp - lo) / (hi - lo)


def distinct_colors(ids, *, cmap="tab10"):
    """Map a set of category ids to distinct colours from a qualitative cmap.

    (See also :func:`idd_figures.lib.palettes.categorical` for a ColorBrewer variant.)
    """
    ids = list(ids)
    cols = plt.get_cmap(cmap)(np.linspace(0, 1, max(len(ids), 1)))
    return {k: cols[i] for i, k in enumerate(ids)}


def ordered_legend(ax):
    """Return ``(handles, labels)`` from ``ax`` with duplicate labels removed."""
    handles, labels = ax.get_legend_handles_labels()
    seen: dict = {}
    for h, lab in zip(handles, labels, strict=False):
        seen.setdefault(lab, h)
    return list(seen.values()), list(seen.keys())


def turn_off_axes(axes):
    """Blank one or more axes (no spines, ticks, or labels)."""
    if not isinstance(axes, (list, tuple, np.ndarray)):
        axes = [axes]
    for ax in np.ravel(axes):
        if ax is not None:
            ax.axis("off")


def ui_tick_formatter(**kwargs):
    """A matplotlib tick ``FuncFormatter`` that rounds via :func:`numbers.smart_ui_format`.

    Apply with ``ax.yaxis.set_major_formatter(ui_tick_formatter(...))`` to give tick
    labels the shared rounding/separator conventions (3 sig figs, middle-dot decimal,
    thin-space thousands, optional ``percentage``/``rate``). ``kwargs`` pass through to
    ``smart_ui_format``.
    """
    from matplotlib.ticker import FuncFormatter

    from idd_figures.lib.numbers import smart_ui_format

    return FuncFormatter(lambda v, _pos: smart_ui_format(v, **kwargs))
