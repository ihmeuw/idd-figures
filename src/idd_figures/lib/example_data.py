"""Deterministic made-up data for vignettes, examples, and tests.

None of this is real — it only exercises the painter/layout data contracts so the
shared figures can be demonstrated without any project data. Every generator is
seeded, so output is reproducible.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

__all__ = [
    "make_timeseries_df",
    "make_forecast_panel_df",
    "make_scatter_df",
    "make_left_behind_df",
    "make_trajectory_df",
    "make_dispersion_stats",
    "make_composition_df",
    "make_admin_polygons",
    "make_admin0_polygons",
    "make_raster",
    "make_admin0_field",
]


def make_timeseries_df(*, n_series=4, year_start=2000, year_end=2050, seed=0):
    """Tidy lines data: columns [series, year_id, value, lo, hi]."""
    rng = np.random.default_rng(seed)
    years = np.arange(year_start, year_end + 1)
    rows = []
    for s in range(n_series):
        level = 50 + 30 * s
        trend = rng.uniform(-0.5, 1.5)
        noise = rng.normal(0, 2, len(years)).cumsum()
        value = level + trend * (years - year_start) + noise
        half = 4 + 0.05 * np.abs(value)
        for yr, v, h in zip(years, value, half, strict=True):
            rows.append({"series": f"series_{s}", "year_id": yr, "value": v,
                         "lo": v - h, "hi": v + h})
    return pd.DataFrame(rows)


def make_forecast_panel_df(*, seed=1):
    """Tidy forecast panel data matching the [group, measure, metric, series,
    year_id, mid, lo, hi] contract. observed has lo/hi = NaN."""
    rng = np.random.default_rng(seed)
    groups = ["Global", "Sub-Saharan Africa", "South Asia", "Latin America", "High-income"]
    measures, metrics = ["inc", "mort"], ["rate", "count"]
    ssps = {"ssp126": 0.6, "ssp245": 1.0, "ssp585": 1.7}
    years = np.arange(2000, 2051)
    anchor = 2023
    rows = []
    for g in groups:
        pop = rng.uniform(2e6, 5e8)
        for measure in measures:
            for metric in metrics:
                base = rng.uniform(20, 200) * (1 if measure == "inc" else 0.3)
                scale = pop if metric == "count" else 1.0
                obs = base + np.cumsum(rng.normal(0, 1.5, (years <= anchor).sum()))
                for yr, v in zip(years[years <= anchor], obs, strict=True):
                    rows.append({"group": g, "measure": measure, "metric": metric,
                                 "series": "observed", "year_id": yr, "mid": v * scale / 1e5,
                                 "lo": np.nan, "hi": np.nan})
                last = obs[-1]
                fut_years = years[years >= anchor]
                for ssp, slope in ssps.items():
                    drift = slope * np.linspace(0, 1, len(fut_years)) * rng.uniform(5, 30)
                    mid = last + drift + np.cumsum(rng.normal(0, 0.8, len(fut_years)))
                    half = 2 + 0.08 * np.abs(mid)
                    for yr, m, h in zip(fut_years, mid, half, strict=True):
                        rows.append({"group": g, "measure": measure, "metric": metric,
                                     "series": ssp, "year_id": yr,
                                     "mid": m * scale / 1e5, "lo": (m - h) * scale / 1e5,
                                     "hi": (m + h) * scale / 1e5})
    return pd.DataFrame(rows)


def make_scatter_df(*, n=120, seed=2):
    """AROC-style scatter: columns [x, y, level, weight, location_name]."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(0.3, 0.9, n)
    y = 0.02 - 0.03 * (x - 0.3) + rng.normal(0, 0.01, n)
    df = pd.DataFrame({"x": x, "y": y, "level": 5, "weight": rng.uniform(1e4, 5e7, n),
                       "location_name": [f"unit_{i}" for i in range(n)]})
    base = pd.DataFrame({"x": [x.mean()], "y": [y.mean()], "level": [3],
                         "weight": [df["weight"].sum()], "location_name": ["National"]})
    return pd.concat([df, base], ignore_index=True)


def make_left_behind_df(*, n=140, seed=3):
    """Left-behind scatter: columns [x, y, bad_prob] (deviations from national)."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 0.05, n)
    y = rng.normal(0, 0.01, n)
    bad_prob = np.clip(0.5 - 6 * x - 30 * y + rng.normal(0, 0.15, n), 0, 1)
    return pd.DataFrame({"x": x, "y": y, "bad_prob": bad_prob})


def make_trajectory_df(*, n_groups=6, seed=4):
    """AID-style trajectories: [location_id, location_name, level_value, aid,
    year_id, focus]."""
    rng = np.random.default_rng(seed)
    years = np.arange(2000, 2024, 4)
    rows = []
    for gid in range(n_groups):
        x0 = rng.uniform(0.3, 0.7)
        a0 = rng.uniform(0.05, 0.2)
        for k, yr in enumerate(years):
            rows.append({"location_id": gid, "location_name": f"country_{gid}",
                         "level_value": x0 + 0.012 * k + rng.normal(0, 0.004),
                         "aid": max(a0 - 0.006 * k + rng.normal(0, 0.003), 0.01),
                         "year_id": yr, "focus": gid < 3})
    return pd.DataFrame(rows)


def make_dispersion_stats(*, n_groups=12, seed=5):
    """Range-bars stats + detailed values.

    Returns ``(stats_df, values_df)``. ``stats_df`` columns: [A0_location_id,
    year_id, lo, hi, med, mean, group_name, super_region_name]. ``values_df``:
    [A0_location_id, year_id, value].
    """
    rng = np.random.default_rng(seed)
    srs = ["Sub-Saharan Africa", "South Asia", "Latin America and Caribbean", "High-income"]
    stats, values = [], []
    for gid in range(n_groups):
        sr = srs[gid % len(srs)]
        center0 = rng.uniform(0.3, 0.7)
        for yr, shift in ((2000, 0.0), (2023, rng.uniform(0.05, 0.2))):
            center = center0 + shift
            spread = rng.uniform(0.05, 0.2)
            units = np.clip(rng.normal(center, spread, 40), 0.01, 0.99)
            stats.append({"A0_location_id": gid, "year_id": yr,
                          "lo": units.min(), "hi": units.max(),
                          "med": np.median(units), "mean": units.mean(),
                          "group_name": f"group_{gid}", "super_region_name": sr})
            for u in units:
                values.append({"A0_location_id": gid, "year_id": yr, "value": u})
    return pd.DataFrame(stats), pd.DataFrame(values)


def make_composition_df(*, n=200, seed=6):
    """Composition data: [health_index, education_index, income_index, hdi]."""
    rng = np.random.default_rng(seed)
    h = rng.uniform(0.3, 0.9, n)
    e = rng.uniform(0.2, 0.85, n)
    i = rng.uniform(0.25, 0.95, n)
    hdi = (h * e * i) ** (1 / 3)
    return pd.DataFrame({"health_index": h, "education_index": e, "income_index": i, "hdi": hdi})


def make_admin_polygons(*, nx=6, ny=4, seed=7):
    """Fake admin GeoDataFrame: a grid of unit-square 'polygons' with location_id + value.

    Lazy-imports geopandas/shapely (optional geo stack) so importing this module never
    requires them.
    """
    import geopandas as gpd  # noqa: PLC0415 -- optional geo dep, lazy on purpose
    from shapely.geometry import box  # noqa: PLC0415

    rng = np.random.default_rng(seed)
    ids, vals, geoms = [], [], []
    for j in range(ny):
        for i in range(nx):
            ids.append(j * nx + i)
            vals.append(float(rng.uniform(0, 100)))
            geoms.append(box(i, j, i + 1, j + 1))
    return gpd.GeoDataFrame({"location_id": ids, "value": vals, "geometry": geoms}, crs="EPSG:4326")


def make_raster(*, ny=20, nx=30, extent=(-10, 20, -5, 15), seed=8):
    """Fake raster: a 2D value array + its ``[lon_min, lon_max, lat_min, lat_max]`` extent."""
    rng = np.random.default_rng(seed)
    return rng.uniform(0, 100, (ny, nx)), list(extent)


def make_admin0_polygons(*, seed=0):
    """REAL Natural Earth Admin-0 countries (110m) as a GeoDataFrame, with a made-up
    ``value`` per country + integer ``location_id`` (and ``name`` when available).

    Downloads Natural Earth data on first use (cartopy's cache); requires the geo stack
    (cartopy + geopandas). Use for realistic global/regional choropleths.
    """
    import cartopy.io.shapereader as shpreader  # noqa: PLC0415 -- optional geo dep, lazy
    import geopandas as gpd  # noqa: PLC0415

    path = shpreader.natural_earth(resolution="110m", category="cultural", name="admin_0_countries")
    ne = gpd.read_file(path)
    ne = ne[ne.geometry.notna()].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    out = gpd.GeoDataFrame(
        {"location_id": range(len(ne)), "value": rng.uniform(0, 100, len(ne)),
         "geometry": ne.geometry.to_numpy()},
        crs=ne.crs,
    )
    name_col = next((c for c in ("ADMIN", "NAME", "SOVEREIGNT") if c in ne.columns), None)
    if name_col is not None:
        out["name"] = ne[name_col].to_numpy()
    return out


@lru_cache(maxsize=8)
def make_admin0_field(*, ny=300, nx=720, extent=(-180, 180, -60, 90), seed=9):
    """A smooth made-up field on a fine lon/lat grid PLUS its per-country mean, sharing one
    value domain (0-100) so a raster map and a choropleth of the same data look alike.

    Returns ``(raster2d, extent, gdf)``:
      * ``raster2d`` — the field, ``np.nan`` outside every country (ocean/lakes show through);
      * ``extent`` — ``[lon0, lon1, lat0, lat1]`` with Antarctica cropped (matches the choropleths);
      * ``gdf`` — Natural Earth Admin-0 countries with ``value`` = the MEAN of the field's pixels
        inside that country (i.e. the choropleth IS the pixel-averaged raster).

    Default grid is 0.5 degrees; cached so the choropleth and raster exemplars share one build.
    Requires the geo stack; downloads Natural Earth data on first use.
    """
    import geopandas as gpd  # noqa: PLC0415 -- optional geo dep, lazy

    world = make_admin0_polygons(seed=seed)[["location_id", "geometry"]]
    x0, x1, y0, y1 = extent
    lon = x0 + (np.arange(nx) + 0.5) * (x1 - x0) / nx
    lat = y1 - (np.arange(ny) + 0.5) * (y1 - y0) / ny  # top->bottom to match origin='upper'
    lon_g, lat_g = np.meshgrid(lon, lat)
    rng = np.random.default_rng(seed)
    # A varied smooth field: a faint latitude trend + many random Gaussian blobs of MIXED sign
    # (so regional highs and lows scatter across both hemispheres, not a monotonic N-S band) +
    # light noise. Absolute amplitudes are arbitrary — land is normalized to 0-100 below.
    field = 0.1 * np.cos(np.radians(lat_g))
    n_blobs = 22
    clon = rng.uniform(x0, x1, n_blobs)
    clat = rng.uniform(y0, y1, n_blobs)
    amp = rng.uniform(-1.0, 1.0, n_blobs)
    width = rng.uniform(300.0, 3000.0, n_blobs)  # deg**2 scale -> ~17-55 deg blobs
    for k in range(n_blobs):
        field += amp[k] * np.exp(-(((lon_g - clon[k]) ** 2 + (lat_g - clat[k]) ** 2) / width[k]))
    field += rng.normal(0, 0.05, (ny, nx))
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon_g.ravel(), lat_g.ravel()), crs=world.crs)
    joined = gpd.sjoin(pts, world, how="inner", predicate="within")
    idx = joined.index.to_numpy()
    on_land = np.zeros(nx * ny, dtype=bool)
    on_land[np.unique(idx)] = True
    # rank-normalize the land pixels to a UNIFORM 0-100: preserves the smooth blob structure
    # (a monotonic remap) but spreads values evenly so every colour/bin is well populated.
    flat = field.ravel()
    lv = flat[on_land]
    ranks = np.empty(len(lv), dtype="float64")
    ranks[lv.argsort()] = np.arange(len(lv))
    normed = np.full(nx * ny, np.nan)
    normed[on_land] = ranks / max(len(lv) - 1, 1) * 100.0
    raster = normed.reshape(ny, nx)
    # per-country mean of the field's pixels -> the choropleth values (the pixel-averaged raster)
    joined = joined.assign(_v=normed[idx])
    means = joined.groupby("location_id")["_v"].mean().rename("value").reset_index()
    gdf = world.merge(means, on="location_id", how="left")
    return raster, list(extent), gdf
