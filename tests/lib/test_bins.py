"""Unit tests for idd_figures.lib.bins."""

import warnings

import numpy as np
import pytest

from idd_figures.lib.bins import categorical_from_bins, clip_to_bins, map_bin_labels


def test_clip_clamps_and_warns():
    with pytest.warns(UserWarning, match="clamped"):
        out = clip_to_bins([-5, 0.5, 10], [0, 1])
    assert out.tolist() == [0.0, 0.5, 1.0]


def test_clip_no_warn_when_in_range():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = clip_to_bins([0.2, 0.8], [0, 1])
    assert out.tolist() == [0.2, 0.8]


def test_categorical_assignment_endpoints():
    # bins [0,1,2,3]: first bin closed-left (<=1), last bin open (>2)
    out = categorical_from_bins([0.0, 0.5, 1.5, 2.5, 5.0], [0, 1, 2, 3])
    assert out.tolist() == [0.0, 0.0, 1.0, 2.0, 2.0]


def test_categorical_nan_stays_nan():
    out = categorical_from_bins([np.nan, 0.5], [0, 1, 2])
    assert np.isnan(out[0])
    assert out[1] == 0.0


def test_labels_basic():
    assert map_bin_labels([0, 1, 2, 3]) == ["0–1", "1–2", "2–3"]


def test_labels_le_ge():
    labs = map_bin_labels([0, 1, 2, 3], le=True, ge=True)
    assert labs[0] == "< 1"
    assert labs[-1] == "> 2"


def test_labels_abbreviate_k_m():
    assert map_bin_labels([0, 1000, 2_000_000], abbreviate=True) == ["0–1K", "1K–2M"]


def test_labels_percent_suffix():
    assert map_bin_labels([0, 50, 100], suffix="%") == ["0%–50%", "50%–100%"]


def test_labels_zero_bin_gives_bare_zero():
    # zero at index 2; the bug being fixed compared an array here
    labs = map_bin_labels([-2, -1, 0, 1, 2], zero_bin=True)
    assert labs[2] == "0"
