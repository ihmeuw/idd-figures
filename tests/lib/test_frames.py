"""Unit tests for idd_figures.lib.frames."""

import pandas as pd

from idd_figures.lib.frames import panel_slice

_DF = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "y", "x"], "v": [10, 20, 30]})


def test_scalar_match():
    assert len(panel_slice(_DF, {"a": 1})) == 2


def test_list_membership():
    assert len(panel_slice(_DF, {"b": ["x"]})) == 2


def test_multi_key_and():
    assert panel_slice(_DF, {"a": 1, "b": "x"})["v"].tolist() == [10]


def test_empty_selection_returns_all():
    assert len(panel_slice(_DF, {})) == 3
