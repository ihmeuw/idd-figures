"""Map painters: draw on a cartopy GeoAxes the layout creates, and return it.

Requires the geo stack (cartopy, geopandas/shapely) — this module imports cartopy
at top, so importing it means "I want maps"; the rest of the library never pulls it.
Painters never own the Figure, never save, and never set the axes *position* (the
layout owns geometry). Data prep (loading, merging, masking, reprojection) is the
caller's job — these receive prepared GeoDataFrames / 2-D arrays.

zorder discipline (load-bearing): ocean = 0, data (choropleth/raster) = 2,
boundaries on top. Aspect is set to 'auto' so cartopy does not lock 1:1 and fight
the GridSpec cell (the layout controls the map's height via the extent aspect).
"""

from __future__ import annotations

import copy as _copy

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from shapely.geometry import box

__all__ = ["basemap_painter", "choropleth_painter", "raster_painter", "disputed_boundary_painter"]

_PC = ccrs.PlateCarree()


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
):
    """Set the map extent + optional ocean / coastlines / borders / grey admin backdrop.

    ``extent`` is ``[lon_min, lon_max, lat_min, lat_max]``. ``base_admin_gdf`` is drawn as
    a light-grey filled backdrop (the "no-data" base), ``admin1_gdf`` as thin outlines.
    ``ocean``/``lakes``/``coastlines``/``borders`` use Natural Earth data (network on first
    use), so they can be toggled off for offline/preview rendering. ``lakes`` is drawn above
    the data so inland water bodies read as water rather than filled land.
    """
    ax.set_extent(extent, crs=_PC)
    ax.set_aspect("auto")  # layout owns aspect; keep cartopy from locking 1:1
    if ocean:
        ax.add_feature(cfeature.OCEAN, facecolor=ocean_color, alpha=ocean_alpha, zorder=0)
    if lakes:
        # drawn ABOVE the data (zorder 5 > data 2) so inland water reads as water, not filled land
        ax.add_feature(cfeature.LAKES, facecolor=ocean_color, alpha=ocean_alpha, zorder=5)
    if coastlines:
        ax.coastlines(linewidth=0.5)
    if borders:
        ax.add_feature(cfeature.BORDERS, linewidth=0.3, edgecolor="gray")
    if base_admin_gdf is not None:
        base_admin_gdf.plot(ax=ax, color=admin_backdrop_color, edgecolor="black",
                            linewidth=0, transform=_PC, zorder=1)
    if admin1_gdf is not None:
        admin1_gdf.boundary.plot(ax=ax, color="darkgrey", linewidth=0.25, transform=_PC, zorder=1)
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
        "column": value_col, "ax": ax, "cmap": cmap, "norm": norm, "legend": False,
        "edgecolor": edgecolor, "linewidth": linewidth, "transform": _PC, "zorder": zorder,
    }
    if missing_color is not None:
        plot_kw["missing_kwds"] = {"color": missing_color}
    gdf.plot(**plot_kw)
    if boundary_gdf is not None:
        boundary_gdf.boundary.plot(ax=ax, color=boundary_color, linewidth=boundary_lw,
                                   transform=_PC, zorder=zorder + 1)
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
        boundary_gdf.boundary.plot(ax=ax, color=boundary_color, linewidth=boundary_lw,
                                   transform=_PC, zorder=zorder + 1)
    return ax


def disputed_boundary_painter(
    ax, disputed_gdf, *, extent, color="darkgrey", linewidth=0.25, linestyle="--", zorder=3
):
    """Overlay disputed boundaries as dashed lines, CLIPPED to ``extent`` first; return ``ax``.

    The clip is essential — without it, disputed lines from the whole globe would be drawn.
    """
    bbox = box(extent[0], extent[2], extent[1], extent[3])
    clipped = disputed_gdf.clip(bbox)
    if len(clipped):
        clipped.boundary.plot(ax=ax, color=color, linewidth=linewidth, linestyle=linestyle,
                              transform=_PC, zorder=zorder)
    return ax
