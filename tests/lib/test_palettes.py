"""Unit tests for idd_figures.lib.palettes."""

import pytest

from idd_figures.lib.palettes import (
    GBD_SUPER_REGION_COLORS,
    GBD_SUPER_REGIONS,
    GREY,
    MED_DARK,
    MED_LIGHT,
    brewer,
    categorical,
)


def test_gbd_colors_cover_all_super_regions():
    assert set(GBD_SUPER_REGION_COLORS) == set(GBD_SUPER_REGIONS)
    assert len(GBD_SUPER_REGIONS) == 7


def test_gbd_colors_are_the_adopted_lsae_hex_strings():
    # house interim standard (2026-08-02): hex STRINGS with hand-chosen semantics
    assert all(isinstance(v, str) and v.startswith("#") for v in GBD_SUPER_REGION_COLORS.values())
    assert GBD_SUPER_REGION_COLORS["High-income"] == "#999999"  # deliberately recessive
    assert GBD_SUPER_REGION_COLORS["Sub-Saharan Africa"] == "#2C7FB8"  # salient blue
    assert len(set(GBD_SUPER_REGION_COLORS.values())) == 7  # all distinct


def test_neutral_companions_exist():
    assert (GREY, MED_DARK, MED_LIGHT) == ("#BDBDBD", "#222222", "#C8C8C8")


def test_brewer_qualitative_full_and_truncated():
    full = brewer("Set2")
    assert len(full) == 8
    assert len(brewer("Set2", 3)) == 3


def test_brewer_continuous_requires_n():
    assert len(brewer("viridis", 5)) == 5
    with pytest.raises(ValueError, match="continuous"):
        brewer("viridis")


def test_categorical_maps_each_key():
    out = categorical(["a", "b", "c"])
    assert len(out) == 3
    assert len({tuple(v) if isinstance(v, (list, tuple)) else v for v in out.values()}) == 3


def test_categorical_cycles_when_more_keys_than_palette():
    keys = [f"k{i}" for i in range(10)]  # Set2 has 8 colours
    out = categorical(keys, palette="Set2")
    assert len(out) == 10  # all keys mapped (colours reused)
