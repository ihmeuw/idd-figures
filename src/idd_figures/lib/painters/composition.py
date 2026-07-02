"""Ternary composition painter (mpltern engine) + standalone layout.

Draws a scatter of three shares on a ternary axis, coloured by a fourth column.
mpltern is an OPTIONAL dependency, imported lazily; the painter draws on a
ternary Axes the layout creates (``projection="ternary"``), like a map's
GeoAxes. ``gridlines`` is exposed so callers can turn mpltern's grid off and
hand-draw their own later.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

__all__ = ["composition_panel", "plot_composition"]


def composition_panel(
    tax,
    df,
    *,
    components,
    color_col,
    cmap="viridis",
    s=6,
    alpha=0.4,
    labels=None,
    gridlines=True,
    normalize=True,
):
    """Scatter three shares on a ternary Axes ``tax``; return ``tax``.

    ``components`` is the (top, left, right) triple of column names. With
    ``normalize`` the three are rescaled to sum to 1 per row. ``tax`` must be a
    ``projection="ternary"`` Axes (the layout creates it).
    """
    a, b, c = components
    data = df[[a, b, c]].to_numpy(dtype="float64")
    if normalize:
        data = data / data.sum(axis=1, keepdims=True)
    tax.scatter(data[:, 0], data[:, 1], data[:, 2], c=df[color_col], cmap=cmap, s=s, alpha=alpha)
    labels = labels or [comp.replace("_index", "").replace("_", " ") for comp in components]
    tax.set_tlabel(labels[0])
    tax.set_llabel(labels[1])
    tax.set_rlabel(labels[2])
    tax.grid(visible=gridlines, linewidth=0.4)
    return tax


def plot_composition(df, *, components, color_col, color_label=None, figsize=(9, 8), **opts):
    """Standalone layout: create the ternary Axes, draw, add a colorbar; return fig.

    Requires the optional ``mpltern`` dependency (imported here so the rest of the
    library never needs it).
    """
    import mpltern  # noqa: F401  -- lazy/optional: registers the "ternary" projection

    fig = plt.figure(figsize=figsize)
    tax = fig.add_subplot(projection="ternary")
    composition_panel(tax, df, components=components, color_col=color_col, **opts)
    if tax.collections:
        fig.colorbar(tax.collections[0], ax=tax, shrink=0.6, pad=0.1, label=color_label or color_col)
    return fig
