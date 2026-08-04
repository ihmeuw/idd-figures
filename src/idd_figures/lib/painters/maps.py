"""Map painters: draw on a cartopy GeoAxes the layout creates, and return it.

Requires the geo stack (cartopy, geopandas/shapely) — this module imports cartopy
at top, so importing it means "I want maps"; the rest of the library never pulls it.
Painters never own the Figure, never save, and never set the axes *position* (the
layout owns geometry). Data prep (loading, merging, masking, reprojection) is the
caller's job — these receive prepared GeoDataFrames / 2-D arrays.

zorder discipline (load-bearing): ocean = 0, data (choropleth/raster) = 2,
boundaries on top. Painters never touch the aspect: the LAYOUT sets it explicitly
and derives the cell box to match the extent ("no automatic anything",
.claude/DECISIONS.md 2026-08-02) — a mismatched box letterboxes visibly and the
layout's guard raises.
"""

from __future__ import annotations

import copy as _copy

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from shapely.geometry import box

from idd_figures.lib.styles import style_kwargs

__all__ = [
    "basemap_painter",
    "choropleth_painter",
    "disputed_boundary_painter",
    "map_cell_painter",
    "raster_painter",
]

_PC = ccrs.PlateCarree()

# concern-dict vocabularies (lib.styles): keys the caller writes -> painter kwargs
_LINE = {"color": "color", "linewidth": "linewidth", "linestyle": "linestyle", "alpha": "alpha"}
_FEATURE_LINE = {  # cartopy features take edgecolor, not color
    "color": "edgecolor",
    "linewidth": "linewidth",
    "linestyle": "linestyle",
    "alpha": "alpha",
}
_FILL = {"color": "color", "alpha": "alpha", "edgecolor": "edgecolor", "linewidth": "linewidth"}


def basemap_painter(
    ax,
    *,
    extent,
    ocean=True,
    lakes=False,
    ocean_color="#A6B6DC",
    ocean_alpha=0.5,
    coastlines=False,
    borders=False,
    base_admin_gdf=None,
    admin1_gdf=None,
    admin_backdrop_color="lightgrey",
    coastline_style=None,
    border_style=None,
    admin1_style=None,
    backdrop_style=None,
):
    """Set the map extent + optional ocean / coastlines / borders / grey admin backdrop.

    ``extent`` is ``[lon_min, lon_max, lat_min, lat_max]``. ``base_admin_gdf`` is drawn as
    a light-grey filled backdrop (the "no-data" base), ``admin1_gdf`` as thin outlines.
    ``ocean``/``lakes``/``coastlines``/``borders`` use Natural Earth data (network on first
    use), so they can be toggled off for offline/preview rendering. ``lakes`` is drawn above
    the data so inland water bodies read as water rather than filled land. The ``*_style``
    dicts (``lib.styles`` vocabulary: color/linewidth/linestyle/alpha, plus edgecolor for
    the backdrop fill) override the drawn defaults per concern, key by key.
    """
    ax.set_extent(extent, crs=_PC)
    if ocean:
        ax.add_feature(cfeature.OCEAN, facecolor=ocean_color, alpha=ocean_alpha, zorder=0)
    if lakes:
        # drawn ABOVE the data (zorder 5 > data 2) so inland water reads as water, not filled land
        ax.add_feature(cfeature.LAKES, facecolor=ocean_color, alpha=ocean_alpha, zorder=5)
    if coastlines:
        ax.coastlines(
            **{"linewidth": 0.5, **style_kwargs(coastline_style, _LINE, "coastline_style")}
        )
    if borders:
        kw = {"linewidth": 0.3, "edgecolor": "gray"}
        kw.update(style_kwargs(border_style, _FEATURE_LINE, "border_style"))
        ax.add_feature(cfeature.BORDERS, **kw)
    if base_admin_gdf is not None:
        kw = {"color": admin_backdrop_color, "edgecolor": "black", "linewidth": 0}
        kw.update(style_kwargs(backdrop_style, _FILL, "backdrop_style"))
        base_admin_gdf.plot(ax=ax, transform=_PC, zorder=1, **kw)
    if admin1_gdf is not None:
        kw = {"color": "darkgrey", "linewidth": 0.25}
        kw.update(style_kwargs(admin1_style, _LINE, "admin1_style"))
        admin1_gdf.boundary.plot(ax=ax, transform=_PC, zorder=1, **kw)
    return ax


def choropleth_painter(
    ax,
    gdf,
    *,
    value_col,
    cmap,
    norm,
    boundary_gdf=None,
    boundary_color="black",
    boundary_lw=0.5,
    edgecolor=None,
    linewidth=0,
    missing_color=None,
    zorder=2,
):
    """Fill polygons in ``gdf`` by ``value_col`` (binned via ``cmap``/``norm``); return ``ax``.

    Admin-agnostic: works for any level — it's just whichever GeoDataFrame you pass.
    ``boundary_gdf`` overlays outlines (e.g. admin0) on top; ``missing_color`` fills
    polygons whose value is NaN (else they fall through to the basemap backdrop).
    """
    plot_kw = {
        "column": value_col,
        "ax": ax,
        "cmap": cmap,
        "norm": norm,
        "legend": False,
        "edgecolor": edgecolor,
        "linewidth": linewidth,
        "transform": _PC,
        "zorder": zorder,
    }
    if missing_color is not None:
        plot_kw["missing_kwds"] = {"color": missing_color}
    gdf.plot(**plot_kw)
    if boundary_gdf is not None:
        boundary_gdf.boundary.plot(
            ax=ax, color=boundary_color, linewidth=boundary_lw, transform=_PC, zorder=zorder + 1
        )
    return ax


def raster_painter(
    ax,
    data2d,
    *,
    extent,
    cmap,
    norm=None,
    vmin=None,
    vmax=None,
    masked_color=None,
    masked_alpha=1.0,
    origin="upper",
    zorder=2,
    boundary_gdf=None,
    boundary_color="black",
    boundary_lw=0.5,
):
    """imshow a 2-D array on the GeoAxes; return ``ax``.

    Two modes: **binned** — ``data2d`` holds integer bin indices, pass a ListedColormap +
    ``vmin=0``/``vmax=n-1``; **continuous** — ``data2d`` holds raw values, pass a continuous
    ``cmap`` + ``norm``. ``extent`` is the DATA extent ``[lon_min, lon_max, lat_min, lat_max]``
    (may differ from the axes view). ``masked_color`` colours NaN/no-data pixels (via
    ``set_bad``); default leaves them transparent (legacy behaviour — ocean shows through).
    Accepts numpy arrays or xarray DataArrays.
    """
    arr = data2d.values if hasattr(data2d, "values") else np.asarray(data2d)
    if masked_color is not None:
        cmap = _copy.copy(cmap)
        cmap.set_bad(color=masked_color, alpha=masked_alpha)
    kw = {"cmap": cmap, "transform": _PC, "extent": extent, "origin": origin, "zorder": zorder}
    if norm is not None:
        kw["norm"] = norm
    else:
        kw["vmin"], kw["vmax"] = vmin, vmax
    ax.imshow(arr, **kw)
    if boundary_gdf is not None:
        boundary_gdf.boundary.plot(
            ax=ax, color=boundary_color, linewidth=boundary_lw, transform=_PC, zorder=zorder + 1
        )
    return ax


def disputed_boundary_painter(
    ax,
    disputed_gdf,
    *,
    extent,
    color="darkgrey",
    linewidth=0.25,
    linestyle="--",
    alpha=1.0,
    zorder=3,
):
    """Overlay disputed boundaries as dashed lines, CLIPPED to ``extent`` first; return ``ax``.

    The clip is essential — without it, disputed lines from the whole globe would be drawn.
    """
    bbox = box(extent[0], extent[2], extent[1], extent[3])
    clipped = disputed_gdf.clip(bbox)
    if len(clipped):
        clipped.boundary.plot(
            ax=ax,
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
            transform=_PC,
            zorder=zorder,
        )
    return ax


def map_cell_painter(
    ax,
    _data=None,
    *,
    extent,
    gdf=None,
    value_col=None,
    raster=None,
    raster_extent=None,
    cmap=None,
    norm=None,
    base_admin_gdf=None,
    admin1_gdf=None,
    boundary_gdf=None,
    disputed_gdf=None,
    ocean=True,
    lakes=False,
    coastlines=False,
    borders=False,
    masked_color=None,
    masked_alpha=1.0,
    missing_color=None,
    draw_data=True,
    panel_letter=None,
    panel_letter_fontsize=24,
    ocean_style=None,
    backdrop_style=None,
    coastline_style=None,
    border_style=None,
    admin1_style=None,
    boundary_style=None,
    poly_style=None,
    disputed_style=None,
    letter_style=None,
):
    """ONE complete map cell: basemap + (choropleth | raster) + disputed lines + letter.

    The composite painter both ``map_panel`` and ``map_facet`` paint into a
    layout-created GeoAxes (``_data`` exists so ``paint(map_cell_painter, None,
    ...)`` works directly). ``draw_data=False`` skips the expensive data draw
    for layout iteration. Never touches aspect or the Figure.

    Every drawn style is reachable through its concern dict (``lib.styles``
    vocabulary, unknown keys raise): ``ocean_style`` {color, alpha} (also fills
    lakes), ``backdrop_style`` {color, alpha, edgecolor, linewidth},
    ``coastline_style``/``admin1_style`` {color, linewidth, linestyle, alpha},
    ``border_style``/``disputed_style`` likewise, ``boundary_style`` {color,
    linewidth} (the ``boundary_gdf`` overlay), ``poly_style`` {edgecolor,
    linewidth} (choropleth polygon edges), ``letter_style`` (matplotlib text
    kwargs, plus x/y in axes fraction). Unset keys keep the painter defaults.
    """
    basemap_painter(
        ax,
        extent=extent,
        ocean=ocean,
        lakes=lakes,
        coastlines=coastlines,
        borders=borders,
        base_admin_gdf=base_admin_gdf,
        admin1_gdf=admin1_gdf,
        coastline_style=coastline_style,
        border_style=border_style,
        admin1_style=admin1_style,
        backdrop_style=backdrop_style,
        **style_kwargs(
            ocean_style, {"color": "ocean_color", "alpha": "ocean_alpha"}, "ocean_style"
        ),
    )
    boundary_kw = style_kwargs(
        boundary_style, {"color": "boundary_color", "linewidth": "boundary_lw"}, "boundary_style"
    )
    if draw_data:
        if gdf is not None:
            choropleth_painter(
                ax,
                gdf,
                value_col=value_col,
                cmap=cmap,
                norm=norm,
                boundary_gdf=boundary_gdf,
                missing_color=missing_color,
                **boundary_kw,
                **style_kwargs(
                    poly_style, {"edgecolor": "edgecolor", "linewidth": "linewidth"}, "poly_style"
                ),
            )
        elif raster is not None:
            raster_painter(
                ax,
                raster,
                extent=raster_extent or extent,
                cmap=cmap,
                norm=norm,
                masked_color=masked_color,
                masked_alpha=masked_alpha,
                boundary_gdf=boundary_gdf,
                **boundary_kw,
            )
        if disputed_gdf is not None:
            disputed_boundary_painter(
                ax,
                disputed_gdf,
                extent=extent,
                **style_kwargs(disputed_style, _LINE, "disputed_style"),
            )
    if panel_letter:
        kw = {"va": "top", "ha": "left", "fontsize": panel_letter_fontsize, "fontweight": "bold"}
        kw.update(letter_style or {})  # matplotlib text kwargs, passed verbatim
        x, y = kw.pop("x", 0.02), kw.pop("y", 0.98)
        ax.text(x, y, panel_letter, transform=ax.transAxes, **kw)
    return ax
