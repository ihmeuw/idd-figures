"""Layout geometry solvers: derive figure sizes and ratios; never eyeball them.

Pure functions, no matplotlib imports. These encode the two facts matplotlib
charges silently and idd-lsae-hdi paid rounds to rediscover (see
integrations/idd-lsae-hdi/survey.md section 6):

- ``wspace``/``hspace`` are charged against the MEAN cell size, so a grid's
  total gap is ``(n-1) * space * mean(cell)`` — :func:`gap_factor` inverts it.
- A fixed-aspect panel's height follows from its WIDTH, which depends on the
  margins and the per-row panel count — :func:`panel_width` /
  :func:`map_row_height` derive it; nothing is hand-picked.

``solve_figure`` combines them: given per-row content heights in inches, it
returns the figure height and the ``height_ratios`` that realise exactly those
heights inside the declared margins. All aspects are in PROJECTED units — for
PlateCarree that is plain degrees, with NO ``1/cos(lat)`` correction (that
squeeze is geopandas-specific and does not apply to our cartopy painters).
"""

from __future__ import annotations

__all__ = [
    "extent_aspect",
    "gap_factor",
    "map_row_height",
    "panel_width",
    "solve_figure",
]


def gap_factor(n, space):
    """Total-size multiplier for ``n`` cells separated by ``space``.

    matplotlib's gridspec charges ``space`` as a fraction of the MEAN cell
    size, so ``n`` cells plus gaps span ``sum(cells) * (1 + (n-1)*space/n)``.
    Exact (from the gridspec cell arithmetic), not an approximation.
    """
    if n < 1:
        msg = "gap_factor needs n >= 1"
        raise ValueError(msg)
    return 1.0 + (n - 1) * space / n


def extent_aspect(extent):
    """Height/width of ``(x0, x1, y0, y1)`` in projected units (degrees for PlateCarree)."""
    x0, x1, y0, y1 = (float(v) for v in extent)
    if x1 <= x0 or y1 <= y0:
        msg = f"degenerate extent {extent}: need x1 > x0 and y1 > y0"
        raise ValueError(msg)
    return (y1 - y0) / (x1 - x0)


def panel_width(fig_width, *, margins, ncols, wspace=0.0):
    """Width in inches of ONE panel in a row of ``ncols`` equal panels.

    ``margins`` is the grids-style dict (figure fractions). ``wspace`` is the
    row's gridspec wspace; each of the ``ncols-1`` gaps costs ``wspace`` times
    the mean panel width, so a panel gets ``usable / (ncols + wspace*(ncols-1))``.
    """
    if ncols < 1:
        msg = "panel_width needs ncols >= 1"
        raise ValueError(msg)
    usable = fig_width * (margins["right"] - margins["left"])
    return usable / (ncols + wspace * (ncols - 1))


def map_row_height(fig_width, *, margins, ncols, aspect, wspace=0.0):
    """Height in inches of a row of ``ncols`` fixed-aspect panels (aspect = h/w)."""
    return panel_width(fig_width, margins=margins, ncols=ncols, wspace=wspace) * aspect


def solve_figure(row_heights, *, margins, hspace=0.0):
    """Figure height + ``height_ratios`` realising ``row_heights`` (inches) exactly.

    ``row_heights`` are the CONTENT heights of the outer grid's rows, top to
    bottom (map rows from :func:`map_row_height`; title/colorbar/legend bands
    as explicit inches — never implicit slack: titles that only clear because
    of leaked dead-band was lsae's bug B6). Returns ``(fig_height, ratios)``
    where ``ratios`` is ``row_heights`` unchanged (gridspec normalises) and

        fig_height = sum(row_heights) * gap_factor(n, hspace) / (top - bottom)

    so after margins and gap charging, each row draws at exactly its height.
    """
    heights = [float(h) for h in row_heights]
    if not heights or any(h <= 0 for h in heights):
        msg = "row_heights must be non-empty and strictly positive"
        raise ValueError(msg)
    span = margins["top"] - margins["bottom"]
    if not 0 < span <= 1:
        msg = f"margins top-bottom span must be in (0, 1], got {span}"
        raise ValueError(msg)
    fig_height = sum(heights) * gap_factor(len(heights), hspace) / span
    return fig_height, list(heights)
