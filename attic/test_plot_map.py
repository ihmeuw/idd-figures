"""Unit tests for idd_figures.plot_map utility functions.

plot_map imports cartopy at module load. cartopy is provided by conda
(environment.yml), not poetry, so on a poetry-only environment (e.g. public
GitHub CI) the import fails. importorskip skips this module cleanly there;
locally inside the idd-figures conda env it runs normally.
"""

import pytest

pytest.importorskip("cartopy")

from idd_figures.plot_map import get_colors, pretty_bin_labels, smart_format


class TestSmartFormat:
    def test_float_that_is_integer(self):
        assert smart_format(5.0) == "5"

    def test_int(self):
        assert smart_format(5) == "5"

    def test_zero(self):
        assert smart_format(0) == "0"

    def test_trailing_zeros_trimmed(self):
        assert smart_format(2.50) == "2.5"

    def test_two_decimal_places_kept(self):
        assert smart_format(2.33) == "2.33"

    def test_rounds_to_two_places(self):
        assert smart_format(2.333) == "2.33"


class TestPrettyBinLabels:
    def test_basic_ranges(self):
        assert pretty_bin_labels([0, 1, 2, 3]) == ["0–1", "1–2", "2–3"]

    def test_le_flag_rewrites_first(self):
        assert pretty_bin_labels([0, 1, 2], le=True)[0] == "< 1"

    def test_ge_flag_rewrites_last(self):
        assert pretty_bin_labels([0, 1, 2], ge=True)[-1] == "> 1"

    def test_equal_endpoints_collapse_to_single_value(self):
        assert pretty_bin_labels([5, 5, 6])[0] == "5"


class TestGetColors:
    def test_returns_requested_count(self):
        assert len(get_colors(5)) == 5

    def test_colors_are_rgba(self):
        assert all(len(c) == 4 for c in get_colors(3))

    def test_cmap_name_changes_colors(self):
        assert get_colors(4, cmap_name="Reds") != get_colors(4, cmap_name="Blues")

    def test_single_bin_raises(self):
        # n_bins == 1 -> division by (n_bins - 1) == 0
        with pytest.raises(ZeroDivisionError):
            get_colors(1)
