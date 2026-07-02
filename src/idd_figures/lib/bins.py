"""Binning primitives for choropleth/raster maps (and any binned figure).

Pure (numpy). Colormap construction lives in :func:`idd_figures.lib.colors.binned_colormap`;
this module clamps values into a bin range, assigns categorical bin indices (for
raster ``imshow``), and formats map-style discrete bin labels.

Two number styles coexist deliberately: the compact **map** style here (comma
grouping + K/M abbreviation + $/% affixes) for bin legends, and the Lancet-style
:func:`idd_figures.lib.numbers.smart_ui_format` for value-in-text. They are not the
same presentation, so map labels keep their own formatter.
"""

from __future__ import annotations

import warnings

import numpy as np

__all__ = ["clip_to_bins", "categorical_from_bins", "map_bin_labels"]


def clip_to_bins(values, bins):
    """Clamp ``values`` into ``[bins[0], bins[-1]]`` so out-of-range data colours into
    the end bins. Returns a numpy array; warns (not prints) if anything was clamped."""
    arr = np.asarray(values, dtype="float64")
    lo, hi = float(bins[0]), float(bins[-1])
    n_out = int(np.count_nonzero((arr < lo) | (arr > hi)))
    if n_out:
        warnings.warn(
            f"clip_to_bins clamped {n_out} value(s) outside [{lo}, {hi}]", stacklevel=2
        )
    return np.clip(arr, lo, hi)


def categorical_from_bins(values, bins):
    """Assign each value to a bin index ``0..n-1`` (``n = len(bins) - 1``); return a
    float array with ``np.nan`` for NaN / unbinned inputs (so raster ``imshow`` masks
    them). Pure — mutates nothing.

    Bins are half-open ``(bins[i], bins[i+1]]`` with the first bin closed on the left
    and the last bin open on the right, matching the legacy map binning.
    """
    arr = np.asarray(values, dtype="float64")
    n = len(bins) - 1
    out = np.full(arr.shape, np.nan)
    for i in range(n):
        if i == 0:
            mask = arr <= bins[i + 1]
        elif i == n - 1:
            mask = arr > bins[i]
        else:
            mask = (arr > bins[i]) & (arr <= bins[i + 1])
        out[mask] = i
    return out


def _smart(val):
    """Comma-grouped compact number: int if integral, else <=2 decimals trimmed."""
    if float(val).is_integer():
        return f"{int(val):,}"
    return f"{val:,.2f}".rstrip("0").rstrip(".")


def map_bin_labels(bins, *, le=False, ge=False, zero_bin=False, prefix="", suffix="",
                   abbreviate=False):
    """Discrete bin labels for a map legend.

    ``le`` / ``ge`` render the first/last bins as ``< x`` / ``> x``; ``zero_bin`` gives
    the bin starting at 0 a bare ``"0"`` label; ``prefix`` (e.g. ``"$"``) / ``suffix``
    (e.g. ``"%"``) affix units; ``abbreviate`` uses K/M for large magnitudes. Uses
    ``" to "`` as the range separator when any bin is negative, else an en-dash.
    """
    bins = list(bins)
    gap = " to " if min(bins) < 0 else "–"

    zi = None
    if zero_bin:
        zeros = np.where(np.asarray(bins) == 0)[0]
        if len(zeros) == 0:
            msg = "zero_bin=True but no 0 found in bins"
            raise ValueError(msg)
        zi = int(zeros[0])  # scalar (legacy compared the array here — the bug we fix)
        if zi == 0:
            le = False
    if suffix == "%":
        abbreviate = False

    def fmt(v):
        if abbreviate:
            a = abs(v)
            if a >= 1_000_000:
                return f"{prefix}{_smart(v / 1e6)}M"
            if a >= 1_000:
                return f"{prefix}{_smart(v / 1e3)}K"
            return f"{prefix}{_smart(v)}"
        if suffix:
            return f"{_smart(v)}{suffix}"
        return _smart(v)

    edges = [fmt(b) for b in bins]
    labels = []
    for i in range(len(edges) - 1):
        left, right = edges[i], edges[i + 1]
        if zero_bin and i == zi:
            labels.append("0")
        elif zero_bin and i == zi + 1:
            labels.append(f"0 - {right}")
        elif left == right:
            labels.append(left)
        else:
            labels.append(f"{left}{gap}{right}")

    if le:
        labels[0] = f"< {edges[1]}"
    if ge:
        labels[-1] = f"> {edges[-2]}"
    if prefix == "$":
        labels = [lab.replace("$", r"\$") for lab in labels]
    return labels
