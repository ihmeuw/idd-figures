"""Colour primitives: discrete bin colours, diverging maps, binned colormaps.

Depends only on matplotlib + numpy. No domain palettes live here — those belong
in ``palettes`` and each repo's config. This is the canonical home for
``get_colors`` (previously duplicated across repos and modules).
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np

__all__ = ["binned_colormap", "diverging_colors", "get_colors", "signed_diverging_cmap"]


def get_colors(n_bins, cmap_name="Reds"):
    """``n_bins`` colours sampled evenly across a named colormap."""
    if n_bins < 2:  # noqa: PLR2004 — a color ramp needs at least 2 colors
        msg = "n_bins must be >= 2"
        raise ValueError(msg)
    cmap = mpl.colormaps[cmap_name]
    return [cmap(i / (n_bins - 1)) for i in range(n_bins)]


def diverging_colors(n_bins, cmap_name="RdBu_r"):
    """``n_bins`` colours sampled across a diverging colormap."""
    return get_colors(n_bins, cmap_name=cmap_name)


def signed_diverging_cmap():
    """Continuous diverging colormap with a hard jump across 0.5 (blue/red).

    Use to colour values by a signed quantity normalised to ``[0, 1]`` so that
    below- and above-zero read as distinct hues, not a continuous fade.
    """
    eps = 1e-6
    return mcolors.LinearSegmentedColormap.from_list(
        "signed_jump",
        [
            (0.0, "#053061"),
            (0.5 - eps, "#4393c3"),
            (0.5 + eps, "#d6604d"),
            (1.0, "#67001f"),
        ],
    )


def binned_colormap(  # noqa: PLR0913 — orthogonal keyword-only colormap options; grouping them would only add ceremony
    bins,
    *,
    base_cmap=None,
    drop_light=0,
    force_white_zero=False,
    diverging=False,
    remove_middle=False,
):
    """Build a discrete ``(cmap, norm, colors)`` for binned values.

    Returns values rather than mutating a config dict (unlike the legacy
    ``create_*_colormap``). ``drop_light`` drops the lightest N colours from a
    sequential map; ``force_white_zero`` whitens the first bin (sequential) or the
    middle bin (diverging, odd bin count).
    """
    bins = np.asarray(bins, dtype="float64")
    n = len(bins) - 1
    if n < 1:
        msg = "need >= 2 bin edges"
        raise ValueError(msg)
    if diverging:
        if remove_middle:
            # drop the central diverging pair (so an odd bin count has a clean centre)
            wide = diverging_colors(n + 2, base_cmap or "RdBu_r")
            mid = (n + 2) // 2
            if force_white_zero:
                colors = [*wide[: mid - 1], (1.0, 1.0, 1.0, 1.0), *wide[mid + 2 :]]
            else:
                colors = wide[: mid - 1] + wide[mid + 1 :]
        else:
            colors = diverging_colors(n, base_cmap or "RdBu_r")
            if force_white_zero and n % 2 == 1:
                colors[n // 2] = (1.0, 1.0, 1.0, 1.0)
    else:
        colors = get_colors(n + drop_light, base_cmap or "Reds")[drop_light:]
        if force_white_zero:
            colors[0] = (1.0, 1.0, 1.0, 1.0)
    cmap = mcolors.ListedColormap(colors)
    norm = mcolors.BoundaryNorm(bins, cmap.N, clip=True)
    return cmap, norm, colors
