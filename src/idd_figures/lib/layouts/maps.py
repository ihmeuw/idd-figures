"""Map layouts: assemble painters into a placed figure.

Imports the geo stack (cartopy + the map painters) at top — importing this module
means "I want maps"; the rest of the library never pulls it.

``map_panel`` builds ONE aspect-locked title / map / legend stack as a ``panel_grid``
with a ``projection=PlateCarree`` map cell. Geometry is explicit (no tight_layout):
the figure height follows the extent's geographic aspect, and every height / font /
margin is a sensible-but-overridable default. ``map_facet`` (multi-panel) comes next.
"""

from __future__ import annotations

import cartopy.crs as ccrs

from idd_figures.lib.layouts.grids import cell, grid, label, paint, panel_grid
from idd_figures.lib.painters.legend import bin_legend_panel
from idd_figures.lib.painters.maps import (
    basemap_painter,
    choropleth_painter,
    disputed_boundary_painter,
    raster_painter,
)

__all__ = ["map_panel"]

_FULL_BLEED = {"left": 0.0, "right": 1.0, "top": 1.0, "bottom": 0.0}


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
        basemap_painter(ax, extent=extent, ocean=ocean, lakes=lakes, coastlines=coastlines,
                        borders=borders, base_admin_gdf=base_admin_gdf)
        if draw_data:
            if gdf is not None:
                choropleth_painter(ax, gdf, value_col=value_col, cmap=cmap, norm=norm,
                                   boundary_gdf=boundary_gdf, missing_color=missing_color)
            elif raster is not None:
                raster_painter(ax, raster, extent=raster_extent or extent, cmap=cmap,
                               norm=norm, masked_color=masked_color, boundary_gdf=boundary_gdf)
            if disputed_gdf is not None:
                disputed_boundary_painter(ax, disputed_gdf, extent=extent)
        if panel_letter:
            ax.text(0.02, 0.98, panel_letter, transform=ax.transAxes, va="top", ha="left",
                    fontsize=panel_letter_fontsize, fontweight="bold")
        return ax

    def _draw_legend(ax, _data=None):
        return bin_legend_panel(ax, colors=colors, labels=bin_labels, mappable=mappable,
                                use_colorbar=use_colorbar, fontsize=legend_fontsize)

    have_legend = colors is not None or mappable is not None
    rows = []
    if title and title_h > 0:
        rows.append({"h": title_h, "content": label(title, fontsize=title_fontsize)})
    if subtitle and subtitle_h > 0:
        rows.append({"h": subtitle_h, "content": label(subtitle, fontsize=subtitle_fontsize)})
    rows.append({"h": map_h, "content": paint(_draw_map, None), "proj": ccrs.PlateCarree(), "name": "map"})
    legend_cell = (
        {"h": legend_h, "content": paint(_draw_legend, None)} if have_legend and legend_h > 0 else None
    )
    title_cell = (
        {"h": legend_title_h, "content": label(legend_title, fontsize=legend_title_fontsize)}
        if legend_title and legend_title_h > 0 else None
    )
    for r in ([title_cell, legend_cell] if legend_title_pos == "above" else [legend_cell, title_cell]):
        if r is not None:
            rows.append(r)

    fig_h = sum(r["h"] for r in rows)
    cells = [
        cell((i, 0), r["content"], projection=r.get("proj"), name=r.get("name"))
        for i, r in enumerate(rows)
    ]
    spec = grid((len(rows), 1), cells, height_ratios=[r["h"] / fig_h for r in rows],
                margins=margins or _FULL_BLEED, wspace=0.0, hspace=hspace)
    return panel_grid(spec, figsize=(fig_width, fig_h))
