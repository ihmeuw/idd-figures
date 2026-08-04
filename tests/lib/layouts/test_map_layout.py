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
    fig = map_panel(
        extent=[0, 6, 0, 4],
        cmap=cmap,
        norm=norm,
        colors=colors,
        ocean=False,
        draw_data=False,
        title="preview",
    )
    assert isinstance(fig, Figure)
    plt.close(fig)


def test_map_panel_legend_title_above_and_below():
    cmap, norm, colors = binned_colormap([0, 50, 100])
    for pos in ("above", "below"):
        fig = map_panel(
            extent=[0, 6, 0, 4],
            cmap=cmap,
            norm=norm,
            colors=colors,
            ocean=False,
            title="t",
            legend_title="v",
            legend_title_pos=pos,
            draw_data=False,
        )
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


def test_map_panel_named_axes_box_matches_extent_and_aspect_explicit():
    fig = map_panel(extent=[0, 6, 0, 4], ocean=False, draw_data=False)
    ax = fig.axes_by_name["map"]
    fw, fh = fig.get_size_inches()
    pos = ax.get_position(original=True)
    assert abs((pos.height * fh) / (pos.width * fw) - 4 / 6) < 1e-9  # box == extent aspect
    assert ax.get_aspect() == 1.0  # explicit, never "auto"
    plt.close(fig)


def test_map_panel_aspect_breaking_margins_raise():
    with pytest.raises(ValueError, match="aspect"):
        map_panel(
            extent=[0, 6, 0, 4],
            ocean=False,
            draw_data=False,
            margins={"left": 0.125, "right": 0.9, "top": 0.93, "bottom": 0.08},
        )


def test_map_panel_aspect_breaking_hspace_raises():
    cmap, norm, colors = binned_colormap([0, 50, 100])
    with pytest.raises(ValueError, match="aspect"):
        map_panel(
            extent=[0, 6, 0, 4],
            cmap=cmap,
            norm=norm,
            colors=colors,
            ocean=False,
            draw_data=False,
            title="t",
            hspace=0.3,
        )


def test_map_facet_rows_bars_aspect_and_names():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    cmap, norm, _ = binned_colormap([0, 25, 50, 75, 100])
    p = {"gdf": gdf, "value_col": "value", "cmap": cmap, "norm": norm}
    fig = map_facet(
        [
            {
                "panels": [dict(p, title=t) for t in ("a", "b", "c")],
                "extent": SYNTHETIC_EXTENT,
                "cbar": "shared",
                "cbar_label": "value",
            },
            {
                "panels": [dict(p)],
                "extent": SYNTHETIC_EXTENT,
                "cbar": "each",
                "cbar_label": "value",
            },
        ],
        fig_width=12,
    )
    fw, fh = fig.get_size_inches()
    want = (SYNTHETIC_EXTENT[3] - SYNTHETIC_EXTENT[2]) / (SYNTHETIC_EXTENT[1] - SYNTHETIC_EXTENT[0])
    for nm in ("map:r0c0", "map:r0c1", "map:r0c2", "map:r1c0"):
        pos = fig.axes_by_name[nm].get_position(original=True)
        assert abs((pos.height * fh) / (pos.width * fw) - want) < 1e-9  # every box fits its extent
    bar = fig.axes_by_name["cbar:r0"].get_position(original=True)
    a = fig.axes_by_name["map:r0c0"].get_position(original=True)
    c = fig.axes_by_name["map:r0c2"].get_position(original=True)
    assert bar.x0 <= a.x0 + 1e-9  # shared bar cell = footprint of the served panels
    assert bar.x1 >= c.x1 - 1e-9
    assert "cbar:r1c0" in fig.axes_by_name  # "each" bars exist per panel
    plt.close(fig)


def test_map_facet_gaps_are_exactly_the_title_allowance_and_preview_marks():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    cmap, norm, colors = binned_colormap([0, 25, 50, 75, 100])
    p = {"gdf": gdf, "value_col": "value", "cmap": cmap, "norm": norm, "colors": colors}
    title_h = 0.4
    fig = map_facet(
        [
            {"panels": [dict(p)], "extent": SYNTHETIC_EXTENT, "cbar": "shared"},
            {"panels": [dict(p), dict(p)], "extent": SYNTHETIC_EXTENT, "cbar": None},
        ],
        fig_width=10,
        panel_title_h=title_h,
        preview=True,
    )
    assert getattr(fig, "_idd_preview", False)  # save_figure will suffix _preview
    _fw, fh = fig.get_size_inches()
    top_map = fig.axes_by_name["map:r0c0"].get_position(original=True)
    bar = fig.axes_by_name["cbar:r0"].get_position(original=True)
    gap_in = (top_map.y0 - bar.y1) * fh
    assert abs(gap_in - title_h) < 1e-9  # inter-row gap == the EXPLICIT title allowance
    plt.close(fig)


def test_map_facet_row_cbar_band_thins_the_ramp():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    cmap, norm, _ = binned_colormap([0, 50, 100])
    p = {"gdf": gdf, "value_col": "value", "cmap": cmap, "norm": norm}
    fig = map_facet(
        [
            {
                "panels": [dict(p)],
                "extent": SYNTHETIC_EXTENT,
                "cbar": "shared",
                "cbar_band": (0.70, 0.92),
                "cbar_h": 0.7,
            },
        ],
        fig_width=10,
    )
    cell_ax = fig.axes_by_name["cbar:r0"]
    ramp = cell_ax.child_axes[0].get_position()
    cell_pos = cell_ax.get_position(original=True)
    frac = ramp.height / cell_pos.height
    assert abs(frac - (0.92 - 0.70)) < 0.02  # ramp thickness follows the row override
    plt.close(fig)


def test_map_facet_title_band_is_its_own_cell_and_grows_fig_by_title_h():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    cmap, norm, _ = binned_colormap([0, 50, 100])

    def rows():
        return [
            {
                "panels": [{"gdf": gdf, "value_col": "value", "cmap": cmap, "norm": norm}],
                "extent": SYNTHETIC_EXTENT,
                "cbar": "shared",
            }
        ]

    title_h, panel_title_h = 0.6, 0.4
    bare = map_facet(rows(), fig_width=10, panel_title_h=panel_title_h, preview=True)
    fig = map_facet(
        rows(),
        fig_width=10,
        title="Spec title",
        title_h=title_h,
        panel_title_h=panel_title_h,
        preview=True,
    )
    _, fh_bare = bare.get_size_inches()
    fw, fh = fig.get_size_inches()
    assert abs(fh - (fh_bare + title_h)) < 1e-9  # figure grows by EXACTLY the title allowance
    band = fig.axes_by_name["title"].get_position(original=True)
    assert abs((1 - band.y1) * fh) < 1e-9  # band is flush with the top: no margin slack above
    assert abs(band.height * fh - title_h) < 1e-9  # band height == declared inches
    top_map = fig.axes_by_name["map:r0c0"].get_position(original=True)
    gap_in = (band.y0 - top_map.y1) * fh
    assert abs(gap_in - panel_title_h) < 1e-9  # gap below band == the panel-title allowance
    want = (SYNTHETIC_EXTENT[3] - SYNTHETIC_EXTENT[2]) / (SYNTHETIC_EXTENT[1] - SYNTHETIC_EXTENT[0])
    assert abs((top_map.height * fh) / (top_map.width * fw) - want) < 1e-9  # aspect survives
    plt.close(bare)
    plt.close(fig)


def test_map_facet_cbar_ticks_pin_natural_units_on_log_ramp():
    import numpy as np
    from matplotlib.colors import LogNorm

    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    ticks = [0.2, 0.5, 1, 2, 5, 10]
    labels = ["0.2", "0.5", "1", "2", "5", "10"]
    fig = map_facet(
        [
            {
                "panels": [
                    {"gdf": gdf, "value_col": "value", "cmap": "viridis", "norm": LogNorm(0.2, 10)}
                ],
                "extent": SYNTHETIC_EXTENT,
                "cbar": "shared",
                "cbar_label": "ratio",
                "cbar_ticks": ticks,
                "cbar_tick_labels": labels,
            }
        ],
        fig_width=10,
        preview=True,
    )
    cax = fig.axes_by_name["cbar:r0"].child_axes[0]  # the ramp inset inside the bar cell
    assert np.allclose(cax.get_xticks(), ticks)  # positions in data (natural) units
    assert [t.get_text() for t in cax.get_xticklabels()] == labels
    plt.close(fig)


def test_map_facet_cbar_ticks_on_discrete_row_raise():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    cmap, norm, colors = binned_colormap([0, 50, 100])
    with pytest.raises(ValueError, match="discrete rows use bin_labels"):
        map_facet(
            [
                {
                    "panels": [
                        {
                            "gdf": gdf,
                            "value_col": "value",
                            "cmap": cmap,
                            "norm": norm,
                            "colors": colors,
                        }
                    ],
                    "extent": SYNTHETIC_EXTENT,
                    "cbar": "shared",
                    "cbar_ticks": [0, 50, 100],
                }
            ]
        )


def test_map_facet_cbar_tick_labels_require_ticks():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    cmap, norm, _ = binned_colormap([0, 50, 100])
    with pytest.raises(ValueError, match="requires cbar_ticks"):
        map_facet(
            [
                {
                    "panels": [{"gdf": gdf, "value_col": "value", "cmap": cmap, "norm": norm}],
                    "extent": SYNTHETIC_EXTENT,
                    "cbar": "shared",
                    "cbar_tick_labels": ["a", "b"],
                }
            ]
        )


def test_map_facet_unknown_cbar_mode_raises():
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet

    gdf = make_synthetic_continents()
    cmap, norm, _ = binned_colormap([0, 50, 100])
    with pytest.raises(ValueError, match="cbar mode"):
        map_facet(
            [
                {
                    "panels": [{"gdf": gdf, "value_col": "value", "cmap": cmap, "norm": norm}],
                    "extent": SYNTHETIC_EXTENT,
                    "cbar": "both",
                }
            ]
        )


def test_world_choropleth_continuous_if_ne_available():
    from idd_figures.lib.examples import exemplar_world_choropleth

    try:
        fig = exemplar_world_choropleth(ocean=False, continuous=True)
    except Exception as e:  # noqa: BLE001 -- network/data availability, not a logic error
        pytest.skip(f"Natural Earth admin0 unavailable: {type(e).__name__}: {e}")
    assert isinstance(fig, Figure)
    plt.close(fig)
