"""Ternary composition layout (mpltern engine).

Owns the Figure for the standalone composition scatter; the DRAWING lives in
:mod:`idd_figures.lib.painters.composition` (the painter takes the ternary Axes).
Split out of ``painters/`` per the painter/layout contract (.claude/DECISIONS.md
2026-08-02): painters never own a Figure. Geometry is explicit — the ternary
axes and the colorbar axes sit at declared figure fractions; no ``shrink``/
``pad`` space-stealing ("no automatic anything").
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from idd_figures.lib.painters.composition import composition_panel

__all__ = ["plot_composition"]

# explicit figure-fraction boxes: (left, bottom, width, height)
_TERNARY_BOX = (0.05, 0.05, 0.72, 0.88)
_CBAR_BOX = (0.86, 0.22, 0.03, 0.56)


def plot_composition(df, *, components, color_col, color_label=None, figsize=(9, 8), **opts):
    """Standalone layout: create the ternary Axes, draw, add a colorbar; return fig.

    Requires the optional ``mpltern`` dependency (imported here so the rest of
    the library never needs it). Axes boxes are explicit figure fractions.
    """
    import mpltern  # noqa: F401  -- lazy/optional: registers the "ternary" projection

    fig = plt.figure(figsize=figsize)
    tax = fig.add_axes(_TERNARY_BOX, projection="ternary")
    composition_panel(tax, df, components=components, color_col=color_col, **opts)
    if tax.collections:
        cax = fig.add_axes(_CBAR_BOX)
        fig.colorbar(tax.collections[0], cax=cax, label=color_label or color_col)
    return fig
