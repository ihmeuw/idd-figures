"""Tidy-frame helpers shared by painters and layouts."""

from __future__ import annotations

__all__ = ["panel_slice"]


def panel_slice(df, selection):
    """Filter a tidy DataFrame to one panel by a ``{column: value | list}`` map.

    Scalar values match by equality; list/tuple/set values match by membership.
    An empty selection returns the frame unchanged.
    """
    mask = None
    for col, val in selection.items():
        if isinstance(val, (list, tuple, set)):
            m = df[col].isin(list(val))
        else:
            m = df[col] == val
        mask = m if mask is None else (mask & m)
    return df if mask is None else df[mask]
