"""Ternary composition painter (mpltern engine).

Draws a scatter of three shares on a ternary axis, coloured by a fourth column.
mpltern is an OPTIONAL dependency, imported lazily; the painter draws on a
ternary Axes the layout creates (``projection="ternary"``), like a map's
GeoAxes. ``gridlines`` is exposed so callers can turn mpltern's grid off and
hand-draw their own later. The standalone figure-owning layout lives in
:mod:`idd_figures.lib.layouts.composition` (painters never own a Figure).
"""

from __future__ import annotations

__all__ = ["composition_panel"]


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
