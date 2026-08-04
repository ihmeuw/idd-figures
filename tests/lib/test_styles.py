"""Unit tests for the cascading style-dict helpers (DECISIONS 2026-08-04)."""

import pytest

from idd_figures.lib.styles import merge_styles, style_kwargs


def test_merge_styles_later_layers_win_per_key():
    fig = {"color": "black", "linewidth": 0.5}
    row = {"linewidth": 0.3}
    panel = {"color": "red"}
    assert merge_styles(fig, row, panel) == {"color": "red", "linewidth": 0.3}


def test_merge_styles_skips_none_and_empty_layers():
    assert merge_styles(None, {"a": 1}, {}, None) == {"a": 1}
    assert merge_styles(None, None) == {}


def test_style_kwargs_translates_only_set_keys():
    mapping = {"color": "boundary_color", "linewidth": "boundary_lw"}
    assert style_kwargs({"linewidth": 0.25}, mapping, "boundary_style") == {"boundary_lw": 0.25}
    assert style_kwargs(None, mapping, "boundary_style") == {}
    assert style_kwargs({}, mapping, "boundary_style") == {}


def test_style_kwargs_unknown_key_raises():
    with pytest.raises(ValueError, match="boundary_style: unknown style keys"):
        style_kwargs({"lw": 1}, {"linewidth": "boundary_lw"}, "boundary_style")
