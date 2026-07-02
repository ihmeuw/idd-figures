"""Unit tests for idd_figures.lib.numbers."""

import numpy as np
import pytest

from idd_figures.lib.numbers import (
    count_scale,
    format_value_ui,
    get_multiplier,
    resolve_scale,
    shared_scale,
    smart_ui_format,
)


class TestGetMultiplier:
    @pytest.mark.parametrize(
        ("n", "mult", "suf"),
        [
            (50, 1.0, ""),
            (500, 1e-2, " (in 100s)"),
            (5000, 1e-3, " (in 1,000s)"),
            (5e4, 1e-4, " (in 10,000s)"),
            (5e5, 1e-5, " (in 100,000s)"),
            (2.6e8, 1e-6, " (in Millions)"),
            (5e9, 1e-9, " (in Billions)"),
        ],
    )
    def test_tiers(self, n, mult, suf):
        assert get_multiplier(n) == (mult, suf)

    def test_negative_uses_magnitude(self):
        assert get_multiplier(-5e8) == get_multiplier(5e8)

    def test_nonstandard_units(self):
        assert get_multiplier(5e7, allow_nonstandard_units=True) == (1e-7, " (in 10 Millions)")
        assert get_multiplier(5e7) == (1e-6, " (in Millions)")  # standard jumps to Millions


class TestGetMultiplierOverride:
    @pytest.mark.parametrize(
        ("ovr", "mult", "suf"),
        [
            (1, 1.0, ""),
            (100, 1e-2, " (in 100s)"),
            (100_000, 1e-5, " (in 100,000s)"),
            (1_000_000, 1e-6, " (in Millions)"),
            (10_000_000, 1e-7, " (in 10 Millions)"),  # legacy: unreachable via override
            (100_000_000, 1e-8, " (in 100 Millions)"),  # legacy: had no branch
        ],
    )
    def test_override_maps_divisor_to_tier(self, ovr, mult, suf):
        # override is independent of the magnitude argument
        assert get_multiplier(0, override_multiplier=ovr) == (mult, suf)

    def test_override_invalid_raises(self):
        with pytest.raises(ValueError, match="override_multiplier"):
            get_multiplier(5, override_multiplier=42)

    def test_count_scale_forwards_override(self):
        assert count_scale(5, override_multiplier=1_000_000) == (1e-6, " (in Millions)")


def test_count_scale_alias():
    assert count_scale(5000) == get_multiplier(5000)


def test_shared_scale_nan_safe():
    assert shared_scale([1e3, np.nan, 5e3]) == (1e-3, " (in 1,000s)")


class TestResolveScale:
    def test_none(self):
        assert resolve_scale(None, [1, 2]) == (1.0, "")

    def test_auto(self):
        assert resolve_scale("auto", [5e5]) == (1e-5, " (in 100,000s)")

    def test_tuple_passthrough(self):
        assert resolve_scale((1e-6, " (in Millions)"), [1]) == (1e-6, " (in Millions)")

    def test_bare_float(self):
        assert resolve_scale(0.5, [1]) == (0.5, "")


class TestSmartUiFormat:
    def test_zero(self):
        assert smart_ui_format(0) == "0·00"

    def test_three_sig_figs(self):
        assert smart_ui_format(1234.5) == "1230"

    def test_percentage(self):
        assert smart_ui_format(0.5, percentage=True) == "50·0"

    def test_millions_word(self):
        assert smart_ui_format(1.5e6, units=True) == "1·50 million"

    def test_thousands_grouping(self):
        assert " " in smart_ui_format(1234567, multiplier_adjustment=False)


def test_format_value_ui():
    assert format_value_ui(1.5, 1.2, 1.8) == "1·50 (95% UI 1·20–1·80)"
