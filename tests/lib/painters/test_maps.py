"""Unit tests for the map painters. cartopy/geopandas are conda-provided; skip cleanly
if absent. Ocean/coastlines/borders are toggled OFF to avoid Natural-Earth downloads."""

import pytest

pytest.importorskip("cartopy")
pytest.importorskip("geopandas")

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.colors import ListedColormap

from idd_figures.lib import example_data as ed
from idd_figures.lib.bins import categorical_from_bins
from idd_figures.lib.colors import binned_colormap
from idd_figures.lib.painters.maps import (
    basemap_painter,
    choropleth_painter,
    disputed_boundary_painter,
    raster_painter,
)

_BINS = [0, 25, 50, 75, 100]


def _geoax():
    fig = plt.figure(figsize=(6, 4))
    ax = fig.add_subplot(projection=ccrs.PlateCarree())
    return fig, ax


def test_basemap_sets_extent_offline():
    fig, ax = _geoax()
    out = basemap_painter(ax, extent=[0, 6, 0, 4], ocean=False)
    assert out is ax
    x0, x1 = ax.get_xlim()
    assert round(x0) == 0
    assert round(x1) == 6
    plt.close(fig)


def test_basemap_ocean_fill_paints_background_offline():
    from matplotlib.colors import to_rgba

    fig, ax = _geoax()
    basemap_painter(ax, extent=[0, 6, 0, 4], ocean="fill", ocean_color="#A6B6DC", ocean_alpha=0.5)
    assert ax.get_facecolor() == to_rgba("#A6B6DC", 0.5)
    # facecolor mode must not add Natural Earth features (offline-safe)
    assert not ax.artists
    plt.close(fig)


def test_basemap_grey_backdrop_draws():
    gdf = ed.make_admin_polygons()
    fig, ax = _geoax()
    basemap_painter(ax, extent=[0, 6, 0, 4], ocean=False, base_admin_gdf=gdf)
    assert len(ax.collections) >= 1
    plt.close(fig)


def test_choropleth_fills_and_outlines():
    gdf = ed.make_admin_polygons()
    cmap, norm, _ = binned_colormap(_BINS)
    fig, ax = _geoax()
    choropleth_painter(ax, gdf, value_col="value", cmap=cmap, norm=norm, boundary_gdf=gdf)
    assert len(ax.collections) >= 2  # fill + boundary
    plt.close(fig)


def test_raster_continuous():
    arr, extent = ed.make_raster()
    fig, ax = _geoax()
    raster_painter(ax, arr, extent=extent, cmap=colormaps["viridis"], vmin=0, vmax=100)
    assert len(ax.images) == 1
    plt.close(fig)


def test_raster_binned_with_mask():
    arr, extent = ed.make_raster()
    _, _, colors = binned_colormap(_BINS)
    idx = categorical_from_bins(arr, _BINS)  # integer bin indices, NaN elsewhere
    fig, ax = _geoax()
    raster_painter(
        ax,
        idx,
        extent=extent,
        cmap=ListedColormap(colors),
        vmin=0,
        vmax=len(colors) - 1,
        masked_color="#f0f0f0",
    )
    assert len(ax.images) == 1
    plt.close(fig)


def test_map_cell_boundary_style_reaches_the_overlay():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.painters.maps import map_cell_painter

    gdf = make_synthetic_continents()
    cmap, norm, _ = binned_colormap(_BINS)
    fig, ax = _geoax()
    map_cell_painter(
        ax,
        extent=SYNTHETIC_EXTENT,
        gdf=gdf,
        value_col="value",
        cmap=cmap,
        norm=norm,
        boundary_gdf=gdf,
        ocean=False,
        boundary_style={"linewidth": 1.2, "color": "red"},
    )
    overlay = ax.collections[-1]  # boundary overlay draws last (zorder above the data)
    assert overlay.get_linewidths()[0] == 1.2
    plt.close(fig)


def test_map_cell_letter_style_overrides_defaults():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT
    from idd_figures.lib.painters.maps import map_cell_painter

    fig, ax = _geoax()
    map_cell_painter(
        ax,
        extent=SYNTHETIC_EXTENT,
        ocean=False,
        draw_data=False,
        panel_letter="A",
        letter_style={"fontsize": 30, "color": "blue", "x": 0.5},
    )
    (txt,) = [t for t in ax.texts if t.get_text() == "A"]
    assert txt.get_fontsize() == 30
    assert txt.get_position()[0] == 0.5
    plt.close(fig)


def test_map_cell_unknown_style_key_raises():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT
    from idd_figures.lib.painters.maps import map_cell_painter

    fig, ax = _geoax()
    with pytest.raises(ValueError, match="ocean_style: unknown style keys"):
        map_cell_painter(ax, extent=SYNTHETIC_EXTENT, ocean=False, ocean_style={"colour": "red"})
    plt.close(fig)


def test_basemap_admin1_style_overrides_hardcoded_default():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents

    gdf = make_synthetic_continents()
    fig, ax = _geoax()
    basemap_painter(
        ax,
        extent=SYNTHETIC_EXTENT,
        ocean=False,
        admin1_gdf=gdf,
        admin1_style={"linewidth": 0.9},
    )
    assert ax.collections[-1].get_linewidths()[0] == 0.9
    plt.close(fig)


def test_disputed_clips_and_draws():
    gdf = ed.make_admin_polygons()  # reuse polygons as stand-in disputed boundaries
    fig, ax = _geoax()
    disputed_boundary_painter(ax, gdf, extent=[0, 3, 0, 2])
    assert len(ax.collections) >= 1
    plt.close(fig)
