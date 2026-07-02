"""Exemplar configs and reference figure builders, on made-up data.

These show the *intended* call-site style: general painters + ``panel_grid`` /
``facet_grid`` driven by small config dicts. They are reference implementations
(tested), so vignettes import and call them rather than defining figure code.

The palettes here are PROVISIONAL placeholders for demonstration only — real
cross-repo palette reconciliation is a separate task.
"""

from __future__ import annotations

import numpy as np
from matplotlib.lines import Line2D

from idd_figures.lib import example_data as ed
from idd_figures.lib.frames import panel_slice
from idd_figures.lib.layouts.grids import cell, grid, label, legend, paint, panel_grid, facet_grid
from idd_figures.lib.numbers import shared_scale
from idd_figures.lib.painters.bars import range_bars_panel
from idd_figures.lib.painters.lines import lines_panel, plot_lines
from idd_figures.lib.painters.scatter import plot_scatter, scatter_panel
from idd_figures.lib.painters.trajectory import plot_trajectory
from idd_figures.lib.style import distinct_colors, size_by_logpop

__all__ = [
    "SSP_COLORS",
    "SSP_ORDER",
    "FORECAST_LINES",
    "SR_COLORS",
    "exemplar_lines",
    "exemplar_forecast_superregion_facet",
    "exemplar_forecast_all_plus_each",
    "exemplar_scatter",
    "exemplar_left_behind",
    "exemplar_trajectory",
    "exemplar_range_bars_two_panel",
    "exemplar_nested_grid",
    "exemplar_composition",
    "exemplar_map_panel",
    "exemplar_world_choropleth",
    "exemplar_pixel_map",
]

# ── provisional exemplar palettes / config (placeholders) ────────────────────
SSP_COLORS = {"observed": "black", "ssp126": "#2c7fb8", "ssp245": "#d95f0e", "ssp585": "#b30000"}
SSP_ORDER = ["ssp126", "ssp245", "ssp585", "observed"]

#: A good exemplar line-config dict: bind the forecast columns/palette/anchor once
#: and splat it into every ``lines_panel`` call (``**FORECAST_LINES``).
FORECAST_LINES = {
    "x": "year_id", "value": "mid", "lo": "lo", "hi": "hi",
    "hue": "series", "hue_order": SSP_ORDER, "colors": SSP_COLORS, "anchor": 2023,
}

SR_COLORS = {
    "Sub-Saharan Africa": "#2C7FB8",
    "South Asia": "#8CC63F",
    "Latin America and Caribbean": "#D6604D",
    "High-income": "#999999",
}


def _forecast_legend():
    handles = [Line2D([0], [0], color=SSP_COLORS[s], lw=2, label=s) for s in SSP_ORDER]
    return handles, [h.get_label() for h in handles]


# ── reference builders ───────────────────────────────────────────────────────
def exemplar_lines(df=None):
    """Standalone multi-series line figure (one painter)."""
    df = ed.make_timeseries_df() if df is None else df
    ax = plot_lines(df, x="year_id", value="value", lo="lo", hi="hi", hue="series",
                    figsize=(8, 5), title="made-up time series", xlabel="year", ylabel="value")
    return ax.figure


def exemplar_forecast_superregion_facet(panel_data=None, *, measure="mort", metric="count"):
    """Small-multiples over groups, shared-y, one shared count multiplier."""
    panel_data = ed.make_forecast_panel_df() if panel_data is None else panel_data
    groups = [g for g in sorted(panel_data["group"].unique()) if g != "Global"]
    d = panel_slice(panel_data, {"measure": measure, "metric": metric, "group": groups})
    vscale = shared_scale(d[["mid", "hi"]]) if metric == "count" else None
    return facet_grid(
        d, lines_panel, col="group", ncol=3, sharey=True,
        panel_kwargs={**FORECAST_LINES, "value_scale": vscale, "show_ci": False},
        titles=lambda info: info["group"], figsize=(13, 6),
        suptitle=f"made-up forecast — {measure}/{metric}",
    )


def exemplar_forecast_all_plus_each(panel_data=None, *, group="Global", measure="mort",
                                    metric="count"):
    """Top-left = all SSPs; the other three = each SSP alone, shared x/y."""
    panel_data = ed.make_forecast_panel_df() if panel_data is None else panel_data
    base = panel_slice(panel_data, {"group": group, "measure": measure, "metric": metric})
    vscale = shared_scale(base[["mid", "hi"]]) if metric == "count" else None
    ssps = ["ssp126", "ssp245", "ssp585"]
    cells = [cell((0, 0), paint(lines_panel, base, **FORECAST_LINES, value_scale=vscale,
                                show_ci=False), name="all", title="All SSPs")]
    for k, s in enumerate(ssps):
        i, j = divmod(k + 1, 2)
        sub = base[base["series"].isin([s, "observed"])]
        cells.append(cell((i, j), paint(lines_panel, sub, **FORECAST_LINES, value_scale=vscale,
                                        show_ci=True), title=s, sharex="all", sharey="all"))
    spec = grid((2, 2), cells, wspace=0.18, hspace=0.3)
    fig = panel_grid(spec, figsize=(12, 8))
    fig.suptitle(f"{group} — {measure}/{metric}")
    return fig


def exemplar_scatter(df=None):
    """AROC-style scatter: progeny sized by population, national overlaid."""
    df = ed.make_scatter_df() if df is None else df
    prog, base = df[df["level"] == 5], df[df["level"] == 3]
    ax = plot_scatter(prog, x="x", y="y", size=("weight", size_by_logpop), color="C1", alpha=0.5,
                      ref_lines={"h": 0, "v": prog["x"].mean()},
                      xlabel="value (start year)", ylabel="AROC", title="made-up AROC scatter")
    scatter_panel(ax, base, x="x", y="y", s_default=120, color="C0", zorder=3)
    return ax.figure


def exemplar_left_behind(df=None):
    """Left-behind scatter: shaded bad quadrant, size by posterior probability."""
    df = ed.make_left_behind_df() if df is None else df

    def prob_sizes(p):
        p = np.asarray(p)
        conds = [p == 0, (p > 0) & (p <= 0.5), (p > 0.5) & (p <= 0.75)]
        return np.select(conds, [10, 60, 120], default=200)

    xmin, ymin = df["x"].min(), df["y"].min()
    ax = plot_scatter(
        df, x="x", y="y", size=("bad_prob", prob_sizes), color="C1", alpha=0.7,
        shade={"x": (xmin, 0), "y": (ymin, 0), "color": "grey", "alpha": 0.15,
               "text": "High-risk\nleft behind"},
        ref_lines={"h": 0, "v": 0}, xlabel="Δ value from national", ylabel="Δ AROC from national",
        title="made-up left-behind",
    )
    return ax.figure


def exemplar_trajectory(df=None):
    """Connected AID trajectories for the focus groups, one path each."""
    df = ed.make_trajectory_df() if df is None else df
    focus = df[df["focus"]]
    colors = distinct_colors(sorted(focus["location_id"].unique()))
    ax = plot_trajectory(focus, x="level_value", y="aid", order="year_id", group="location_id",
                         colors=colors, xlabel="country level", ylabel="AID",
                         title="made-up trajectories")
    return ax.figure


def exemplar_range_bars_two_panel(stats_df=None, values_df=None):
    """Two-panel dispersion: absolute range bars (top) + log2 relative (bottom)."""
    if stats_df is None:
        stats_df, values_df = ed.make_dispersion_stats()
    common = {"group_col": "A0_location_id", "years": (2000, 2023),
              "color_by": "super_region_name", "colors": SR_COLORS}
    cells = [
        cell((0, 0), paint(range_bars_panel, stats_df, values_df=values_df, **common), name="abs"),
        cell((1, 0), paint(range_bars_panel, stats_df, relative=True, **common), sharex="abs"),
    ]
    spec = grid((2, 1), cells, height_ratios=[3, 1], hspace=0.08, margins={"bottom": 0.16})
    return panel_grid(spec, figsize=(8, 10))


def exemplar_nested_grid(panel_data=None, *, figsize=(12, 11)):
    """Nested grid: (measure x group) outer, (count/rate) inner, gutters + legend.

    Demonstrates nested GridSpec + reserved label/legend slots + one shared count
    multiplier across every count subpanel + shared x within each count/rate pair.
    """
    panel_data = ed.make_forecast_panel_df() if panel_data is None else panel_data
    groups = [g for g in sorted(panel_data["group"].unique()) if g != "Global"][:2]
    measures = ["inc", "mort"]
    cdat = panel_slice(panel_data, {"metric": "count", "group": groups})
    cscale = shared_scale(cdat[["mid", "hi"]])

    cells = [cell((0, j + 1), label(g)) for j, g in enumerate(groups)]  # top gutter: group labels
    for i, measure in enumerate(measures):
        cells.append(cell((i + 1, 0), label(measure.upper(), rotation=90)))  # left gutter
        for j, g in enumerate(groups):
            count_name = f"{measure}_{g}_count"
            inner = []
            for r, metric in enumerate(["count", "rate"]):
                d = panel_slice(panel_data, {"group": g, "measure": measure, "metric": metric})
                vs = cscale if metric == "count" else None
                inner.append(cell((r, 0), paint(lines_panel, d, **FORECAST_LINES, value_scale=vs,
                                                 show_ci=False),
                                  name=(count_name if metric == "count" else None),
                                  sharex=(count_name if metric == "rate" else None)))
            cells.append(cell((i + 1, j + 1), grid((2, 1), inner, hspace=0.1)))
    cells.append(cell((3, slice(1, 3)), legend(_forecast_legend())))

    spec = grid((4, 3), cells, height_ratios=[0.05, 1, 1, 0.12], width_ratios=[0.05, 1, 1],
                margins={"left": 0.05, "right": 0.98, "top": 0.95, "bottom": 0.04},
                wspace=0.18, hspace=0.25)
    return panel_grid(spec, figsize=figsize)


def exemplar_composition(df=None):
    """Ternary composition triangle (requires the optional ``mpltern`` dependency)."""
    from idd_figures.lib.painters.composition import plot_composition

    df = ed.make_composition_df() if df is None else df
    return plot_composition(df, components=("health_index", "education_index", "income_index"),
                            color_col="hdi", color_label="HDI",
                            labels=["health", "education", "income"])


def exemplar_map_panel(*, draw_data=True):
    """Single aspect-locked map (choropleth) with title + legend + legend-title + panel letter.

    Requires the geo stack (cartopy/geopandas), imported lazily. ``draw_data=False`` shows
    the layout skeleton without the expensive map draw.
    """
    from idd_figures.lib.bins import map_bin_labels
    from idd_figures.lib.colors import binned_colormap
    from idd_figures.lib.layouts.maps import map_panel

    gdf = ed.make_admin_polygons()
    bins = [0, 20, 40, 60, 80, 100]
    cmap, norm, colors = binned_colormap(bins, base_cmap="Reds")
    labels = map_bin_labels(bins, ge=True)
    return map_panel(
        gdf=gdf, value_col="value", extent=[0, 6, 0, 4],
        cmap=cmap, norm=norm, colors=colors, bin_labels=labels, boundary_gdf=gdf,
        ocean=False, title="Made-up choropleth — map_panel demo", legend_title="value",
        panel_letter="A", fig_width=8, draw_data=draw_data,
    )


def _world_map(kind, *, continuous, ocean=True):
    """Shared builder for the global maps. ``kind`` is ``"choropleth"`` or ``"raster"``; both
    draw the SAME data (``make_admin0_field``) on the SAME extent / cmap (viridis) / bins / value
    domain (0-100), binned or continuous, so the four combinations look alike. The choropleth
    values are the per-country pixel mean of the raster. Oceans + lakes are shown when ``ocean``.
    """
    import matplotlib
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    from idd_figures.lib.bins import map_bin_labels
    from idd_figures.lib.colors import binned_colormap
    from idd_figures.lib.layouts.maps import map_panel

    raster, extent, gdf = ed.make_admin0_field()
    bins = [0, 20, 40, 60, 80, 100]
    content = ({"gdf": gdf, "value_col": "value"} if kind == "choropleth"
               else {"raster": raster, "raster_extent": extent})
    common = {"extent": extent, "boundary_gdf": gdf, "ocean": ocean, "lakes": ocean,
              "legend_title": "value", "fig_width": 12}
    if continuous:
        cmap = matplotlib.colormaps["viridis"]
        norm = Normalize(0, 100)
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        return map_panel(cmap=cmap, norm=norm, mappable=sm, use_colorbar=True,
                         title=f"World {kind} — continuous ramp", **content, **common)
    cmap, norm, colors = binned_colormap(bins, base_cmap="viridis")
    return map_panel(cmap=cmap, norm=norm, colors=colors, bin_labels=map_bin_labels(bins, ge=True),
                     title=f"World {kind} — binned", **content, **common)


def exemplar_world_choropleth(*, continuous=False, ocean=True):
    """Global Admin-0 choropleth; each country's value is the mean of the raster field's pixels
    inside it (see :func:`exemplar_pixel_map`). ``continuous=True`` swaps discrete bins for a
    colorbar. Requires the geo stack; downloads Natural Earth data on first use.
    """
    return _world_map("choropleth", continuous=continuous, ocean=ocean)


def exemplar_pixel_map(*, continuous=False, ocean=True):
    """Global raster/pixel map of the SAME field the choropleth averages — values only over land;
    oceans and lakes show through. Same extent / cmap / bins as the choropleth so they look alike.
    ``continuous=True`` swaps discrete bins for a colorbar. Requires the geo stack.
    """
    return _world_map("raster", continuous=continuous, ocean=ocean)
