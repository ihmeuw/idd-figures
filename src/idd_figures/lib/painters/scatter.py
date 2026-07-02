"""General scatter painter: size/colour encoding, reference lines, shaded region.

Absorbs the AROC scatter, the "left behind" quadrant scatter, and the background
scatter of the AID figures — they differ only in encodings (all parameters).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

__all__ = ["scatter_panel", "plot_scatter"]


def _resolve_size(size, df):
    """Resolve ``size`` to a scalar or per-point array.

    ``size`` may be None, a scalar, a column name, or ``(column, fn)`` where
    ``fn`` maps the column values to sizes (e.g. ``("pop", size_by_logpop)``).
    """
    if size is None:
        return None
    if isinstance(size, (int, float)):
        return size
    if isinstance(size, str):
        return df[size].to_numpy()
    if isinstance(size, tuple) and len(size) == 2:
        col, fn = size
        return fn(df[col])
    msg = "size must be None, a scalar, a column name, or (column, fn)"
    raise TypeError(msg)


def scatter_panel(
    ax,
    df,
    *,
    x,
    y,
    size=None,
    s_default=30,
    color=None,
    hue=None,
    colors=None,
    alpha=None,
    edgecolors="black",
    linewidths=0.5,
    marker="o",
    label=None,
    zorder=2,
    ref_lines=None,
    shade=None,
    xlabel=None,
    ylabel=None,
):
    """Draw a scatter onto ``ax`` and return ``ax``.

    ``size`` encodes marker size (see :func:`_resolve_size`). With ``hue`` +
    ``colors`` (a dict), points are coloured by group. ``ref_lines`` is
    ``{"h": [...], "v": [...]}``. ``shade`` is ``{"x": (x0, x1), "y": (y0, y1),
    "color": ..., "alpha": ..., "text": ...}`` for a highlighted region.
    """
    if shade is not None:
        (x0, x1), (y0, y1) = shade["x"], shade["y"]
        ax.add_patch(
            Rectangle(
                (x0, y0), x1 - x0, y1 - y0,
                facecolor=shade.get("color", "grey"), alpha=shade.get("alpha", 0.15),
                edgecolor="none", zorder=0,
            )
        )
        if "text" in shade:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, shade["text"], ha="center", va="center",
                    fontsize=11, color="0.25", zorder=1)

    if hue is not None and colors:
        for key, g in df.groupby(hue):
            sg = _resolve_size(size, g)
            ax.scatter(g[x], g[y], s=s_default if sg is None else sg, color=colors.get(key),
                       alpha=alpha, edgecolors=edgecolors, linewidths=linewidths, marker=marker,
                       label=str(key), zorder=zorder)
    else:
        s = _resolve_size(size, df)
        ax.scatter(df[x], df[y], s=s_default if s is None else s, color=color, alpha=alpha,
                   edgecolors=edgecolors, linewidths=linewidths, marker=marker, label=label,
                   zorder=zorder)

    if ref_lines:
        for yv in np.atleast_1d(ref_lines.get("h", [])):
            ax.axhline(yv, color="grey", ls="--", lw=0.8, zorder=1)
        for xv in np.atleast_1d(ref_lines.get("v", [])):
            ax.axvline(xv, color="grey", ls="--", lw=0.8, alpha=0.5, zorder=1)

    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    return ax


def plot_scatter(df, *, ax=None, figsize=(8, 6), title=None, **opts):
    """Standalone one-painter layout for a scatter; returns the Axes."""
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    scatter_panel(ax, df, **opts)
    if title is not None:
        ax.set_title(title)
    return ax
