"""Synthetic low-vertex "continents": instant map data for layout work and tests.

Six hand-drawn blobs (~8 vertices each) in lon/lat with per-shape values — no
shapefile, no network, milliseconds to draw. This is the layout-iteration
fixture (2026-08-02 ruling): real shapefiles (simplified variant) are for real
figures; full-resolution geometry is an explicit opt-in for finals only.

geopandas/shapely are imported lazily — importing this module costs nothing.
"""

from __future__ import annotations

__all__ = ["SYNTHETIC_EXTENT", "make_synthetic_continents"]

SYNTHETIC_EXTENT = (-180.0, 180.0, -60.0, 80.0)

# (name, value, ring of (lon, lat)) — deliberately crude, single ring each
_SHAPES = [
    ("borea", 15.0, [(-165, 20), (-120, 18), (-70, 30), (-55, 48), (-75, 66),
                     (-115, 72), (-150, 65), (-168, 45)]),
    ("austra", 35.0, [(-82, 8), (-58, 2), (-48, -18), (-62, -42), (-75, -52),
                      (-84, -30), (-90, -8)]),
    ("eurasia", 55.0, [(-10, 38), (25, 34), (75, 30), (125, 35), (160, 55),
                       (140, 70), (70, 74), (10, 62), (-12, 50)]),
    ("meridia", 75.0, [(-15, 32), (15, 30), (40, 18), (48, -8), (30, -32),
                       (12, -34), (-8, -12), (-18, 12)]),
    ("oceania", 92.0, [(112, -12), (140, -10), (154, -24), (148, -40), (122, -38),
                       (110, -24)]),
    ("insula", 48.0, [(60, -44), (78, -42), (84, -52), (70, -58), (56, -54)]),
]


def make_synthetic_continents():
    """Return a GeoDataFrame ``[name, value, geometry]`` of the six synthetic shapes.

    ``value`` spans ~15-92 so any 0-100 binning/ramp exercises multiple colours.
    Add derived columns for multi-panel demos (``gdf.assign(v2=...)``).
    """
    import geopandas as gpd
    from shapely.geometry import Polygon

    names, values, geoms = zip(
        *[(n, v, Polygon(ring)) for n, v, ring in _SHAPES], strict=True
    )
    return gpd.GeoDataFrame(
        {"name": list(names), "value": list(values)}, geometry=list(geoms), crs="EPSG:4326"
    )
