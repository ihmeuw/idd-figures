"""Cascading concern-specific style dicts (house ruling, DECISIONS 2026-08-04).

Every hardcoded style in the map stack is reachable through a small dict named
for its concern (``boundary_style``, ``ocean_style``, ``title_style``, ...).
Dicts cascade with KEY-LEVEL merging — figure-level -> row-level -> panel-level
— so a missing dict, or a missing key inside one, falls back one level up and
ends at the painter's own defaults. Line/fill concerns use a fixed key
vocabulary (``color``/``linewidth``/``linestyle``/``alpha``, plus ``edgecolor``
for filled shapes) translated to each painter's kwarg names; text concerns pass
through to matplotlib verbatim.
"""

from __future__ import annotations

__all__ = ["merge_styles", "style_kwargs"]


def merge_styles(*layers):
    """Merge style dicts lowest-priority FIRST; later layers win per key.

    ``None``/empty layers are skipped, so
    ``merge_styles(figure_d, row_d, panel_d)`` implements the cascade directly.
    """
    out = {}
    for layer in layers:
        if layer:
            out.update(layer)
    return out


def style_kwargs(style, mapping, what):
    """Translate a concern dict's keys to a painter's kwarg names via ``mapping``.

    Only keys the caller actually SET are returned, so the painter's defaults
    keep working one level down. Unknown keys raise — a typo must never
    silently style nothing.
    """
    if not style:
        return {}
    unknown = set(style) - set(mapping)
    if unknown:
        msg = f"{what}: unknown style keys {sorted(unknown)}; allowed: {sorted(mapping)}"
        raise ValueError(msg)
    return {mapping[k]: v for k, v in style.items()}
