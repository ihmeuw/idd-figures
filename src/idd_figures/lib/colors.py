"""Colour primitives: discrete bin colours, diverging maps, binned colormaps.

Depends only on matplotlib + numpy. No domain palettes live here — those belong
in ``palettes`` and each repo's config. This is the canonical home for
``get_colors`` (previously duplicated across repos and modules).
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np

__all__ = [
    "binned_colormap",
    "clipped_diverging_cmap",
    "diverging_colors",
    "get_colors",
    "signed_diverging_cmap",
]


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


def clipped_diverging_cmap(name="RdYlBu", *, lo=0.375, hi=0.625, n=256):
    """CONTINUOUS diverging colormap with the middle band removed (hard seam at 0.5).

    Samples ``name`` at ``n`` steps and deletes the ``[lo, hi)`` FRACTION of the
    ramp (defaults cut the washed-out middle 25%), so under symmetric limits
    (``vmin=-x, vmax=+x``) the visible seam lands exactly on zero and the two
    sides never blur. The continuous counterpart of ``binned_colormap(...,
    remove_middle=True)``; adopted from idd-lsae-hdi's ``clipped_diverging_cmap``
    with the 256-sample indices re-expressed as fractions.

    ``lo`` and ``hi`` must be symmetric about 0.5 (``lo == 1 - hi``) — an
    off-centre cut would silently move the seam off zero.
    """
    if not 0 <= lo < hi <= 1:
        msg = f"need 0 <= lo < hi <= 1, got lo={lo}, hi={hi}"
        raise ValueError(msg)
    if abs(lo - (1 - hi)) > 1e-9:  # noqa: PLR2004 -- float-equality tolerance, not a tunable
        msg = f"lo/hi must be symmetric about 0.5 (lo == 1 - hi), got lo={lo}, hi={hi}"
        raise ValueError(msg)
    base = mpl.colormaps[name]
    colors = base(np.linspace(0, 1, n))
    keep = np.vstack([colors[: round(lo * n)], colors[round(hi * n) :]])
    return mcolors.ListedColormap(keep, name=f"{name}_clipped")


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

    ``remove_middle`` is symmetric by construction — equal colour counts on each
    side of the seam. Even bin counts drop the pair straddling the seam (n/2 per
    side, no centre bin); odd bin counts get a white centre bin with one colour
    dropped from EACH side (an odd count implies the white centre;
    ``force_white_zero`` is redundant there and an error for even counts).
    """
    bins = np.asarray(bins, dtype="float64")
    n = len(bins) - 1
    if n < 1:
        msg = "need >= 2 bin edges"
        raise ValueError(msg)
    if diverging:
        if remove_middle:
            if n % 2 == 0:
                if force_white_zero:
                    msg = "force_white_zero needs a centre bin; even bin counts have none"
                    raise ValueError(msg)
                # drop the pair straddling the seam -> n/2 colours per side
                wide = diverging_colors(n + 2, base_cmap or "RdBu_r")
                mid = (n + 2) // 2
                colors = wide[: mid - 1] + wide[mid + 1 :]
            else:
                # odd: white centre bin, one colour dropped from EACH side of the seam
                wide = diverging_colors(n + 1, base_cmap or "RdBu_r")
                m = (n + 1) // 2
                colors = [*wide[: m - 1], (1.0, 1.0, 1.0, 1.0), *wide[m + 1 :]]
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
