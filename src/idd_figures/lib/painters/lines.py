"""General line / time-series painter (the canonical atom) + standalone layout.

Draws one or more lines over an ordered x, with an optional [lo, hi] band and an
optional anchor vline. Reusable for any "series of <something> over an ordered
axis" figure. Domain enters only through column names, colours, and labels — all
parameters. Never makes a Figure, never saves; sets only its own axis labels.

Per-mark appearance (colour, width, style, transparency, markers, band colour) is
a *painter* concern and lives here; fonts, ticks, rounding, titles, and placement
are *layout/caller* concerns set on the axes/figure around the painter.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from idd_figures.lib.numbers import resolve_scale

__all__ = ["lines_panel", "plot_lines"]


def _per(value, key):
    """Resolve a per-series style arg: ``dict`` -> ``value[key]``, else ``value``.

    Lets every style knob accept either one value (applied to all series) or a dict
    keyed by hue value.
    """
    if isinstance(value, dict):
        return value.get(key)
    return value


def lines_panel(
    ax,
    df,
    *,
    x="x",
    value="value",
    lo=None,
    hi=None,
    hue=None,
    hue_order=None,
    colors=None,
    labels=None,
    value_scale=None,
    ylabel=None,
    xlabel=None,
    anchor=None,
    show_ci=True,
    lw=1.7,
    linestyle=None,
    alpha=None,
    marker=None,
    markersize=None,
    band_color=None,
    band_alpha=0.22,
):
    """Draw line(s) onto ``ax`` and return ``ax``.

    ``df`` is tidy rows for one panel. With ``hue`` set, one line is drawn per
    value of that column (order via ``hue_order``); ``colors`` / ``labels`` are
    dicts keyed by hue value. ``value_scale`` (see :func:`numbers.resolve_scale`)
    multiplies plotted values and appends a unit suffix to ``ylabel``.

    Per-mark appearance knobs — ``colors``, ``lw``, ``linestyle``, ``alpha``,
    ``marker``, ``markersize``, ``band_color``, ``band_alpha`` — each accept either a
    single value (applied to every series) or a dict keyed by hue value.
    ``band_color`` defaults to the line colour.
    """
    colors = colors if colors is not None else {}
    labels = labels or {}
    scale, suffix = resolve_scale(value_scale, df[value])

    if hue is None:
        series = [(None, df)]
    else:
        order = hue_order if hue_order is not None else sorted(df[hue].dropna().unique())
        series = [(s, df[df[hue] == s]) for s in order]

    for s, g_raw in series:
        if len(g_raw) == 0:
            continue
        g = g_raw.sort_values(x)
        color = _per(colors, s)
        lab = labels.get(s, s) if isinstance(labels, dict) else labels
        if show_ci and lo and hi and g[lo].notna().any():
            ax.fill_between(
                g[x],
                g[lo] * scale,
                g[hi] * scale,
                color=_per(band_color, s) or color,
                alpha=_per(band_alpha, s),
                lw=0,
            )
        ax.plot(
            g[x],
            g[value] * scale,
            color=color,
            lw=_per(lw, s),
            linestyle=_per(linestyle, s) or "-",
            alpha=_per(alpha, s),
            marker=_per(marker, s),
            markersize=_per(markersize, s),
            label=lab,
        )

    if anchor is not None:
        ax.axvline(anchor, color="grey", ls=":", lw=0.8)
    ax.margins(x=0.01)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel + suffix)
    return ax


def plot_lines(df, *, ax=None, figsize=(8, 5), title=None, **opts):
    """Standalone one-painter layout. Returns the Axes (so it also works as a
    painter when an ``ax`` is supplied). The caller owns IO."""
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    lines_panel(ax, df, **opts)
    if title is not None:
        ax.set_title(title)
    return ax
