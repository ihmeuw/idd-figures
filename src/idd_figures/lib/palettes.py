"""Shared palettes, leaning on ColorBrewer (matplotlib ships the Brewer maps).

Two things live here:

* ``brewer`` / ``categorical`` — convenient access to ColorBrewer palettes, since
  we use them heavily.
* The GBD super-region colour map — a neutral ColorBrewer default (NOT an official
  GBD palette). Repos override by passing their own ``colors=``; nothing is forced.
"""

from __future__ import annotations

import matplotlib as mpl

__all__ = [
    "GBD_SUPER_REGIONS",
    "GBD_SUPER_REGION_COLORS",
    "brewer",
    "categorical",
]

#: The seven GBD super-region names (canonical keys; the hex are what may change).
GBD_SUPER_REGIONS = (
    "Central Europe, Eastern Europe, and Central Asia",
    "High-income",
    "Latin America and Caribbean",
    "North Africa and Middle East",
    "South Asia",
    "Southeast Asia, East Asia, and Oceania",
    "Sub-Saharan Africa",
)

# GBD_SUPER_REGION_COLORS is defined at the bottom of the module (it uses categorical()).

_QUALITATIVE_MAX = 20  # ListedColormaps at/under this size are treated as discrete palettes


def brewer(name, n=None):
    """Colours of a ColorBrewer (or any named) colormap as a list.

    Qualitative Brewer maps (``Set1``/``Set2``/``Dark2``/``Paired``/...) return their
    discrete palette entries (the first ``n`` if given). Continuous maps require ``n``
    and are sampled evenly. (viridis-style maps are 256-entry ListedColormaps, so the
    size check below routes them through the continuous branch.)
    """
    cmap = mpl.colormaps[name]
    colors = getattr(cmap, "colors", None)
    if colors is not None and len(colors) <= _QUALITATIVE_MAX:
        cols = list(colors)
        return cols[:n] if n else cols
    if n is None:
        msg = f"{name!r} is a continuous colormap; pass n="
        raise ValueError(msg)
    return [cmap(i / (n - 1)) for i in range(n)]


def categorical(keys, *, palette="Set2"):
    """Map an ordered set of ``keys`` to ColorBrewer qualitative colours.

    ``palette`` must be a qualitative Brewer map. If there are more keys than the
    palette has colours, colours are cycled — pick a larger palette (e.g. ``Set3`` /
    ``Paired`` = 12) if you need every key distinct.
    """
    keys = list(keys)
    base = brewer(palette)
    return {k: base[i % len(base)] for i, k in enumerate(keys)}


#: Default GBD super-region colours. NOT an official GBD palette — a neutral, reproducible
#: ColorBrewer mapping so figures have sensible defaults out of the box. Override per
#: repo/figure with your own ``colors=``; swap the palette here if a house GBD colour
#: standard is adopted.
GBD_SUPER_REGION_COLORS = categorical(GBD_SUPER_REGIONS, palette="Dark2")
