"""Connected-trajectory painter: path(s) through (x, y) with start/end markers.

A connected scatter ordered by a sequence column (e.g. year), optionally one
path per group, with distinct markers at the first and last point of each path.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

__all__ = ["plot_trajectory", "trajectory_panel"]


def trajectory_panel(
    ax,
    df,
    *,
    x,
    y,
    order,
    group=None,
    colors=None,
    color="C0",
    lw=1.5,
    marker_s=45,
    end_s=140,
    end_markers=("v", "^"),
    edgecolors="k",
    xlabel=None,
    ylabel=None,
    zorder=2,
):
    """Draw connected trajectory(ies) onto ``ax`` and return ``ax``.

    Points within a path are ordered by ``order``. With ``group`` set, one path
    is drawn per group (colour from ``colors[group]`` else ``color``).
    ``end_markers`` are the (first, last) markers placed at the path ends.
    """
    colors = colors or {}

    def _draw(g, c):
        g = g.sort_values(order)
        ax.plot(g[x], g[y], "-", color=c, lw=lw, zorder=zorder)
        ax.scatter(g[x], g[y], s=marker_s, color=c, edgecolors=edgecolors, zorder=zorder + 1)
        if end_markers and len(g):
            lo, hi = g[order].min(), g[order].max()
            for val, mk in ((lo, end_markers[0]), (hi, end_markers[1])):
                pt = g[g[order] == val]
                ax.scatter(
                    pt[x],
                    pt[y],
                    s=end_s,
                    color=c,
                    edgecolors=edgecolors,
                    marker=mk,
                    zorder=zorder + 2,
                )

    if group is None:
        _draw(df, color)
    else:
        for key, g in df.groupby(group):
            _draw(g, colors.get(key, color))

    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    return ax


def plot_trajectory(df, *, ax=None, figsize=(8, 6), title=None, **opts):
    """Standalone one-painter layout for a trajectory; returns the Axes."""
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    trajectory_panel(ax, df, **opts)
    if title is not None:
        ax.set_title(title)
    return ax
