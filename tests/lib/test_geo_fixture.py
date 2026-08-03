"""Unit tests for the synthetic-continents layout fixture."""

import pytest

pytest.importorskip("geopandas")

from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents


def test_fixture_shapes_are_valid_and_inside_the_extent():
    gdf = make_synthetic_continents()
    assert len(gdf) == 6
    assert gdf.crs is not None
    assert gdf.geometry.is_valid.all()
    minx, miny, maxx, maxy = gdf.total_bounds
    assert minx >= SYNTHETIC_EXTENT[0] and maxx <= SYNTHETIC_EXTENT[1]
    assert miny >= SYNTHETIC_EXTENT[2] and maxy <= SYNTHETIC_EXTENT[3]


def test_fixture_values_span_multiple_bins():
    gdf = make_synthetic_continents()
    assert gdf["value"].between(0, 100).all()
    # values must land in >= 3 of the canonical 0-100 quartile bins for demo ramps
    assert gdf["value"].floordiv(25).nunique() >= 3
