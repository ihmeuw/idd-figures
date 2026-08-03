"""Map layouts: assemble painters into a placed figure.

Imports the geo stack (cartopy + the map painters) at top — importing this module
means "I want maps"; the rest of the library never pulls it.

``map_panel`` builds ONE aspect-locked title / map / legend stack as a ``panel_grid``
with a ``projection=PlateCarree`` map cell. Geometry is explicit (no tight_layout):
the figure height follows the extent's geographic aspect, the map cell's aspect is
set EXPLICITLY (never "auto" — .claude/DECISIONS.md 2026-08-02), and a guard raises
when margins/hspace would break the derived box. ``map_facet`` (multi-panel) comes next.
"""

from __future__ import annotations

import cartopy.crs as ccrs

from idd_figures.lib.layouts.geometry import (
    extent_aspect,
    map_row_height,
    solve_figure,
)
from idd_figures.lib.layouts.grids import cell, grid, label, paint, panel_grid
from idd_figures.lib.painters.legend import bin_legend_panel
from idd_figures.lib.painters.maps import map_cell_painter

__all__ = ["map_facet", "map_panel"]

_FULL_BLEED = {"left": 0.0, "right": 1.0, "top": 1.0, "bottom": 0.0}


def _assert_map_box_matches_extent(fig, ax, extent, *, tol=0.01):
    """Raise when the map cell's allocated box aspect diverges from the extent aspect.

    The aspect is explicit (no ``set_aspect("auto")``), so a mismatched box would
    letterbox the map — we fail loudly at build time instead of drawing it wrong.
    """
    fw, fh = fig.get_size_inches()
    pos = ax.get_position(original=True)
    box = (pos.height * fh) / (pos.width * fw)
    want = (extent[3] - extent[2]) / (extent[1] - extent[0])
    if abs(box - want) > tol * want:
        msg = (
            f"map cell box aspect {box:.4f} != extent aspect {want:.4f}: margins/hspace "
            "broke the derived geometry. Use the defaults or aspect-preserving values; "
            "arbitrary margins need the geometry solver (map_facet)."
        )
        raise ValueError(msg)


def map_panel(
    *,
    extent,
    cmap=None,
    norm=None,
    colors=None,
    bin_labels=None,
    gdf=None,
    value_col=None,
    raster=None,
    raster_extent=None,
    base_admin_gdf=None,
    boundary_gdf=None,
    disputed_gdf=None,
    ocean=True,
    lakes=False,
    coastlines=False,
    borders=False,
    masked_color=None,
    missing_color=None,
    fig_width=12,
    title_h=0.5,
    subtitle_h=0.0,
    legend_h=0.75,
    legend_title_h=0.25,
    legend_title_pos="below",
    margins=None,
    hspace=0.0,
    title=None,
    subtitle=None,
    legend_title=None,
    title_fontsize=22,
    subtitle_fontsize=16,
    legend_title_fontsize=18,
    legend_fontsize=14,
    panel_letter=None,
    panel_letter_fontsize=24,
    use_colorbar=False,
    mappable=None,
    draw_data=True,
):
    """Assemble a single map figure and return it.

    Provide EITHER ``gdf`` + ``value_col`` (choropleth) OR ``raster`` (+ optional
    ``raster_extent``). ``cmap``/``norm``/``colors``/``bin_labels`` come from
    ``colors.binned_colormap`` + ``bins.map_bin_labels`` (compute once, pass in).
    Rows (top->bottom): title / subtitle / map / legend / legend-title; any row with
    zero height (or no text) is omitted. ``draw_data=False`` renders the full layout
    but skips the expensive map draw (fast layout iteration). Heights are inches;
    the map row's height follows ``fig_width * (lat-span / lon-span)`` so the map is
    undistorted. The caller saves (see ``io.save_figure``)."""
    aspect = (extent[3] - extent[2]) / (extent[1] - extent[0])
    map_h = fig_width * aspect

    def _draw_map(ax, _data=None):
        return map_cell_painter(
            ax,
            extent=extent,
            gdf=gdf,
            value_col=value_col,
            raster=raster,
            raster_extent=raster_extent,
            cmap=cmap,
            norm=norm,
            base_admin_gdf=base_admin_gdf,
            boundary_gdf=boundary_gdf,
            disputed_gdf=disputed_gdf,
            ocean=ocean,
            lakes=lakes,
            coastlines=coastlines,
            borders=borders,
            masked_color=masked_color,
            missing_color=missing_color,
            draw_data=draw_data,
            panel_letter=panel_letter,
            panel_letter_fontsize=panel_letter_fontsize,
        )

    def _draw_legend(ax, _data=None):
        return bin_legend_panel(
            ax,
            colors=colors,
            labels=bin_labels,
            mappable=mappable,
            use_colorbar=use_colorbar,
            fontsize=legend_fontsize,
        )

    have_legend = colors is not None or mappable is not None
    rows = []
    if title and title_h > 0:
        rows.append({"h": title_h, "content": label(title, fontsize=title_fontsize)})
    if subtitle and subtitle_h > 0:
        rows.append({"h": subtitle_h, "content": label(subtitle, fontsize=subtitle_fontsize)})
    rows.append(
        {"h": map_h, "content": paint(_draw_map, None), "proj": ccrs.PlateCarree(), "name": "map"}
    )
    legend_cell = (
        {"h": legend_h, "content": paint(_draw_legend, None)}
        if have_legend and legend_h > 0
        else None
    )
    title_cell = (
        {"h": legend_title_h, "content": label(legend_title, fontsize=legend_title_fontsize)}
        if legend_title and legend_title_h > 0
        else None
    )
    order = [title_cell, legend_cell] if legend_title_pos == "above" else [legend_cell, title_cell]
    rows.extend(r for r in order if r is not None)

    fig_h = sum(r["h"] for r in rows)
    cells = [
        cell((i, 0), r["content"], projection=r.get("proj"), name=r.get("name"))
        for i, r in enumerate(rows)
    ]
    spec = grid(
        (len(rows), 1),
        cells,
        height_ratios=[r["h"] / fig_h for r in rows],
        margins=margins or _FULL_BLEED,
        wspace=0.0,
        hspace=hspace,
    )
    fig = panel_grid(spec, figsize=(fig_width, fig_h))
    if not draw_data:
        fig._idd_preview = True  # noqa: SLF001 -- own convention; save_figure suffixes _preview
    ax_map = fig.axes_by_name["map"]
    ax_map.set_aspect(1.0, adjustable="box")  # lon/lat degrees draw equal; the box already matches
    _assert_map_box_matches_extent(fig, ax_map, extent)
    return fig


def _legend_paint(ax, _data=None, **kw):
    return bin_legend_panel(ax, **kw)


def _panel_mappable(panel):
    """Build the colorbar mappable from the panel's declared cmap/norm.

    NEVER harvested from drawn artists (``ax.collections[0]`` is the fragile
    pattern the lsae survey flagged) — bars work identically in preview mode.
    """
    from matplotlib.cm import ScalarMappable

    sm = ScalarMappable(norm=panel["norm"], cmap=panel["cmap"])
    sm.set_array([])
    return sm


# ramp band inside a bar cell: high enough that ticks + label fit BELOW it,
# inside the same cell — a bar's ink never leaks into the inter-row gap
_BAR_BAND = {"bin_bottom": 0.55, "bin_top": 0.95}


def _bar_content(panel, bar_label, fontsize, band=None):
    """Grid content for one colorbar/legend cell: discrete swatches if the panel
    declares ``colors`` (the house default), else a continuous bar from cmap/norm.

    ``band`` overrides the ramp's (bin_bottom, bin_top) within the cell — the
    knob for "the bar is too thick/thin" without touching the cell's height."""
    kw = dict(_BAR_BAND) if band is None else {"bin_bottom": band[0], "bin_top": band[1]}
    if panel.get("colors") is not None:
        return paint(
            _legend_paint,
            None,
            colors=panel["colors"],
            labels=panel.get("bin_labels"),
            fontsize=fontsize,
            **kw,
        )
    return paint(
        _legend_paint,
        None,
        mappable=_panel_mappable(panel),
        use_colorbar=True,
        cbar_label=bar_label,
        fontsize=fontsize,
        **kw,
    )


def map_facet(
    rows,
    *,
    fig_width=16.0,
    projection=None,
    wspace=0.02,
    panel_title_h=0.4,
    cbar_h=0.85,
    bottom_pad_h=0.15,
    side_margins=(0.02, 0.98),
    cbar_fontsize=11,
    preview=False,
):
    """Multi-panel map figure: rows of fixed-aspect map panels + group colorbar rows.

    ``rows`` is a list of dicts::

        {"panels": [{"gdf": ..., "value_col": ...,        # or "raster": ...
                     "cmap": ..., "norm": ...,             # or "vmin"/"vmax"
                     "colors": ..., "bin_labels": ...,     # optional: discrete legend
                     "title": ..., "name": ...}, ...],
         "extent": (x0, x1, y0, y1),                       # per row
         "cbar": "shared" | "each" | None,
         "cbar_label": str | list[str],
         "cbar_h": inches,                                  # optional per-row cell height
         "cbar_band": (bin_bottom, bin_top)}                # optional ramp thickness in the cell

    Everything is derived (``lib.layouts.geometry``): panel widths charge
    ``wspace`` against the mean panel, row heights follow the extent aspect in
    projected units, and inter-row gaps are an EXPLICIT title allowance
    (``panel_title_h`` inches — titles never survive on accidental slack).
    Colorbars/legends are grid CELLS spanning the panels they serve; their
    drawn size inside the cell is the legend painter's inset knobs; a "shared"
    bar uses the FIRST panel's colour declaration. Map cells get explicit
    aspect (never "auto") and the box guard raises on mismatch. ``preview=True``
    skips data draws and Natural Earth features and marks the figure so
    ``io.save_figure`` suffixes ``_preview``. Named axes come back via
    ``fig.axes_by_name`` (defaults ``map:r{i}c{j}`` / ``cbar:r{i}[c{j}]``).
    """
    proj = projection or ccrs.PlateCarree()
    margins_lr = {"left": side_margins[0], "right": side_margins[1]}

    outer_cells, heights, map_names = [], [], []
    out_i = 0
    for i, row in enumerate(rows):
        panels, extent = row["panels"], row["extent"]
        k = len(panels)
        for p in panels:
            if p.get("norm") is None and p.get("cmap") is not None:
                from matplotlib.colors import Normalize

                p["norm"] = Normalize(p["vmin"], p["vmax"])
        inner = grid(
            (1, k),
            [
                cell(
                    (0, j),
                    paint(
                        map_cell_painter,
                        None,
                        extent=extent,
                        gdf=p.get("gdf"),
                        value_col=p.get("value_col"),
                        raster=p.get("raster"),
                        raster_extent=p.get("raster_extent"),
                        cmap=p.get("cmap"),
                        norm=p.get("norm"),
                        base_admin_gdf=p.get("base_admin_gdf"),
                        boundary_gdf=p.get("boundary_gdf"),
                        missing_color=p.get("missing_color"),
                        ocean=not preview and p.get("ocean", False),
                        draw_data=not preview,
                    ),
                    projection=proj,
                    title=p.get("title"),
                    name=p.get("name") or f"map:r{i}c{j}",
                )
                for j, p in enumerate(panels)
            ],
            wspace=wspace,
        )
        map_names.append(([p.get("name") or f"map:r{i}c{j}" for j, p in enumerate(panels)], extent))
        outer_cells.append(cell((out_i, 0), inner))
        heights.append(
            map_row_height(
                fig_width, margins=margins_lr, ncols=k, aspect=extent_aspect(extent), wspace=wspace
            )
        )
        out_i += 1

        mode = row.get("cbar")
        if mode is None:
            continue
        labels = row.get("cbar_label")
        band = row.get("cbar_band")  # (bin_bottom, bin_top) of the ramp within its cell
        if mode == "shared":
            outer_cells.append(
                cell(
                    (out_i, 0),
                    _bar_content(panels[0], labels, cbar_fontsize, band=band),
                    name=f"cbar:r{i}",
                )
            )
        elif mode == "each":
            per = labels if isinstance(labels, (list, tuple)) else [labels] * k
            bar_row = grid(
                (1, k),
                [
                    cell(
                        (0, j),
                        _bar_content(p, per[j], cbar_fontsize, band=band),
                        name=f"cbar:r{i}c{j}",
                    )
                    for j, p in enumerate(panels)
                ],
                wspace=wspace,
            )
            outer_cells.append(cell((out_i, 0), bar_row))
        else:
            msg = f"unknown cbar mode {mode!r}: use 'shared', 'each', or None"
            raise ValueError(msg)
        heights.append(row.get("cbar_h", cbar_h))
        out_i += 1

    n = len(heights)
    content = sum(heights)
    hspace = (
        0.0 if n == 1 else panel_title_h / (content / n)
    )  # every gap = exactly the title allowance
    fig_h = content + (n - 1) * panel_title_h + panel_title_h + bottom_pad_h
    margins = {**margins_lr, "top": 1 - panel_title_h / fig_h, "bottom": bottom_pad_h / fig_h}
    _, ratios = solve_figure(heights, margins=margins, hspace=hspace)

    spec = grid((n, 1), outer_cells, height_ratios=ratios, margins=margins, hspace=hspace)
    fig = panel_grid(spec, figsize=(fig_width, fig_h))
    if preview:
        fig._idd_preview = True  # noqa: SLF001 -- own convention; save_figure suffixes _preview
    for names, extent in map_names:
        for nm in names:
            ax = fig.axes_by_name[nm]
            ax.set_aspect(1.0, adjustable="box")
            _assert_map_box_matches_extent(fig, ax, extent)
    return fig
