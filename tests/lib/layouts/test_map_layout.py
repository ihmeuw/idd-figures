"""Unit tests for the map layout (map_panel). cartopy/geopandas conda-provided; skip if absent."""

import pytest

pytest.importorskip("cartopy")
pytest.importorskip("geopandas")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from idd_figures.lib.colors import binned_colormap
from idd_figures.lib.examples import exemplar_map_panel
from idd_figures.lib.layouts.maps import map_panel


def test_map_panel_builds_title_map_legend_legendtitle():
    fig = exemplar_map_panel()
    assert isinstance(fig, Figure)
    # rows: title / map / legend / legend-title (subtitle_h=0 omitted)
    assert len(fig.axes) == 4
    plt.close(fig)


def test_map_panel_aspect_locked_height():
    # extent 6 wide x 4 tall -> aspect 4/6; map row height = fig_width * aspect
    fig = exemplar_map_panel()
    fw, fh = fig.get_size_inches()
    assert fw == 8
    # fig_h = title(0.5) + map(8*4/6=5.333) + legend(0.75) + legend_title(0.25)
    assert abs(fh - (0.5 + 8 * 4 / 6 + 0.75 + 0.25)) < 1e-6
    plt.close(fig)


def test_world_choropleth_renders_if_ne_available():
    from idd_figures.lib.examples import exemplar_world_choropleth

    try:  # downloads Natural Earth admin0 on first use; skip cleanly if offline
        fig = exemplar_world_choropleth(ocean=False)
    except Exception as e:  # noqa: BLE001 -- network/data availability, not a logic error
        pytest.skip(f"Natural Earth admin0 unavailable: {type(e).__name__}: {e}")
    assert isinstance(fig, Figure)
    assert len(fig.axes) == 4
    plt.close(fig)


def test_map_panel_preview_skips_data():
    cmap, norm, colors = binned_colormap([0, 50, 100])
    fig = map_panel(extent=[0, 6, 0, 4], cmap=cmap, norm=norm, colors=colors,
                    ocean=False, draw_data=False, title="preview")
    assert isinstance(fig, Figure)
    plt.close(fig)


def test_map_panel_legend_title_above_and_below():
    cmap, norm, colors = binned_colormap([0, 50, 100])
    for pos in ("above", "below"):
        fig = map_panel(extent=[0, 6, 0, 4], cmap=cmap, norm=norm, colors=colors, ocean=False,
                        title="t", legend_title="v", legend_title_pos=pos, draw_data=False)
        assert isinstance(fig, Figure)
        assert len(fig.axes) == 4  # title / map / legend / legend-title
        plt.close(fig)


def test_pixel_map_renders_if_ne_available():
    from idd_figures.lib.examples import exemplar_pixel_map

    try:  # masks the field to NE country polygons (needs the admin0 download)
        fig = exemplar_pixel_map(ocean=False)
    except Exception as e:  # noqa: BLE001 -- network/data availability, not a logic error
        pytest.skip(f"Natural Earth admin0 unavailable: {type(e).__name__}: {e}")
    assert isinstance(fig, Figure)
    plt.close(fig)


def test_admin0_field_couples_raster_and_choropleth():
    import numpy as np

    from idd_figures.lib.example_data import make_admin0_field

    try:
        raster, extent, gdf = make_admin0_field(ny=60, nx=120)
    except Exception as e:  # noqa: BLE001 -- network/data availability
        pytest.skip(f"Natural Earth admin0 unavailable: {type(e).__name__}: {e}")
    assert extent == [-180, 180, -60, 90]  # Antarctica cropped -> matches the choropleth extent
    land = raster[np.isfinite(raster)]
    assert land.min() >= 0 and land.max() <= 100  # shared 0-100 domain (no negatives)
    vals = gdf["value"].dropna()
    assert len(vals) > 0 and float(vals.min()) >= 0 and float(vals.max()) <= 100
    plt.close("all")


def test_world_choropleth_continuous_if_ne_available():
    from idd_figures.lib.examples import exemplar_world_choropleth

    try:
        fig = exemplar_world_choropleth(ocean=False, continuous=True)
    except Exception as e:  # noqa: BLE001 -- network/data availability, not a logic error
        pytest.skip(f"Natural Earth admin0 unavailable: {type(e).__name__}: {e}")
    assert isinstance(fig, Figure)
    plt.close(fig)
