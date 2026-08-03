"""Number presentation for figures: axis multipliers + value-with-UI text.

Shared by every painter/layout that puts a raw magnitude on a readable axis or
writes a formatted "mean (95% UI: lo-hi)" string, so number formatting stays
consistent across repos. Pure (no matplotlib); depends only on numpy.

Note: this is the corrected port of the legacy ``number_functions.get_multiplier``.
The auto (by-magnitude) path was already correct; the ``override_multiplier`` path
is restored here via a single divisor -> (multiplier, suffix) table so every tier
stays consistent (``key == 1 / multiplier``). The legacy code duplicated the
``1_000_000`` key for "10 Millions" — making that tier unreachable via override —
and had no ``100_000_000`` branch, so those two tiers were wrong/missing.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "compact",
    "count_scale",
    "format_value_ui",
    "get_multiplier",
    "resolve_scale",
    "shared_scale",
    "smart_ui_format",
]

# override_multiplier -> (multiplier, suffix). The key is the divisor (= 1 / multiplier),
# consistent across every tier. Single source of truth for the override path so the
# keys can't drift out of sync (the legacy parallel-elif version duplicated 1_000_000).
_OVERRIDE_TIERS = {
    1: (1.0, ""),
    100: (1e-2, " (in 100s)"),
    1_000: (1e-3, " (in 1,000s)"),
    10_000: (1e-4, " (in 10,000s)"),
    100_000: (1e-5, " (in 100,000s)"),
    1_000_000: (1e-6, " (in Millions)"),
    10_000_000: (1e-7, " (in 10 Millions)"),
    100_000_000: (1e-8, " (in 100 Millions)"),
    1_000_000_000: (1e-9, " (in Billions)"),
}


def compact(value):
    """Scalar k/M tick notation: ``5000 -> "5k"``, ``2_500_000 -> "2.5M"``, ``350 -> "350"``.

    The drop-in for per-tick GDP/count labels on log axes (adopted from
    idd-lsae-hdi's ``_tick_label``, which was thousands-only and ignored
    negatives — this one keys tiers on ``abs(value)``). Distinct from
    :func:`smart_ui_format` (Lancet prose style) and ``bins.map_bin_labels``
    (range-over-edges labels); the three presentations coexist deliberately.
    """
    kilo, mega = 1e3, 1e6
    v = float(value)
    if abs(v) >= mega:
        return f"{v / mega:g}M"
    if abs(v) >= kilo:
        return f"{v / kilo:g}k"
    return f"{v:g}"


def get_multiplier(number, *, scale=2, allow_nonstandard_units=False, override_multiplier=None):  # noqa: PLR0911 -- explicit tier ladder (documented legacy port); tracked debt
    """Display multiplier + label suffix for a magnitude (auto, by magnitude).

    Returns ``(multiplier, suffix)`` so that ``value * multiplier`` lands on a
    readable axis and ``suffix`` names the unit, e.g. ``(1e-6, " (in Millions)")``.

    ``scale`` controls how far into a tier a value must reach before the tier
    switches (threshold ``scale * 10**k``). With ``allow_nonstandard_units`` the
    "10 Millions" / "100 Millions" tiers are available; otherwise magnitudes jump
    from Millions straight to Billions (the standard journal units).

    ``override_multiplier`` forces a tier by its divisor (``key == 1 / multiplier``),
    e.g. ``1_000_000`` -> Millions, ``10_000_000`` -> 10 Millions, ``100_000_000`` ->
    100 Millions; it is looked up in :data:`_OVERRIDE_TIERS` independent of ``number``.
    """
    if override_multiplier is not None:
        try:
            return _OVERRIDE_TIERS[override_multiplier]
        except KeyError:
            msg = (
                f"override_multiplier must be one of {sorted(_OVERRIDE_TIERS)}; "
                f"got {override_multiplier!r}"
            )
            raise ValueError(msg) from None
    n = abs(float(number))
    if n < scale * 1e2:
        return 1.0, ""
    if n < scale * 1e3:
        return 1e-2, " (in 100s)"
    if n < scale * 1e4:
        return 1e-3, " (in 1,000s)"
    if n < scale * 1e5:
        return 1e-4, " (in 10,000s)"
    if n < scale * 1e6:
        return 1e-5, " (in 100,000s)"
    if allow_nonstandard_units:
        if n < scale * 1e7:
            return 1e-6, " (in Millions)"
        if n < scale * 1e8:
            return 1e-7, " (in 10 Millions)"
        if n < scale * 1e9:
            return 1e-8, " (in 100 Millions)"
        return 1e-9, " (in Billions)"
    if n < scale * 1e9:
        return 1e-6, " (in Millions)"
    return 1e-9, " (in Billions)"


def count_scale(max_value, *, scale=2, allow_nonstandard_units=False, override_multiplier=None):
    """Multiplier + suffix for a single magnitude (thin alias of get_multiplier)."""
    return get_multiplier(
        max_value,
        scale=scale,
        allow_nonstandard_units=allow_nonstandard_units,
        override_multiplier=override_multiplier,
    )


def shared_scale(values, *, scale=2, allow_nonstandard_units=False):
    """One ``(multiplier, suffix)`` for a whole set of values (NaN-safe).

    Compute once in a layout and pass it to every panel that shares an axis so
    the panels agree on units. ``values`` may be any array-like / DataFrame.
    """
    arr = np.asarray(values, dtype="float64")
    m = float(np.nanmax(np.abs(arr))) if arr.size else 0.0
    if not np.isfinite(m):
        m = 0.0
    return get_multiplier(m, scale=scale, allow_nonstandard_units=allow_nonstandard_units)


def resolve_scale(value_scale, values):
    """Resolve a painter's ``value_scale`` argument to ``(multiplier, suffix)``.

    ``value_scale`` may be:
      * ``None`` / ``1`` -> no scaling, ``(1.0, "")``;
      * ``"auto"`` -> computed from ``values`` via :func:`shared_scale`;
      * a ``(multiplier, suffix)`` tuple -> used verbatim (a layout's shared scale);
      * a bare number -> used as the multiplier with no suffix.
    """
    if value_scale is None or value_scale in (1, 1.0):
        return 1.0, ""
    if isinstance(value_scale, tuple):
        return value_scale
    if isinstance(value_scale, str) and value_scale == "auto":
        return shared_scale(values)
    return float(value_scale), ""


def smart_ui_format(  # noqa: C901, PLR0912, PLR0915 -- Lancet formatter ported whole; splitting it is tracked debt
    val,
    *,
    units=False,
    reference_val=None,
    percentage=False,
    rate=False,
    small_number=None,
    multiplier_adjustment=True,
):
    """Format a number with 3 significant figures, Lancet-style.

    Uses a middle-dot decimal separator and thin-space thousands grouping;
    supports percentage (``*100``) and rate (``*100000``) scaling and million/
    billion unit words. ``reference_val`` lets a UI bound use the mean's unit.
    """
    val = float(val)
    original = val
    if percentage:
        val *= 100
        if reference_val is not None:
            reference_val = float(reference_val) * 100
    elif rate:
        val *= 100000
        if reference_val is not None:
            reference_val = float(reference_val) * 100000

    use_millions = use_billions = False
    if multiplier_adjustment and not percentage and not rate:
        check = reference_val if reference_val is not None else original
        if abs(check) >= 1e9:
            use_billions = True
            val /= 1e9
        elif abs(check) >= 1e6:
            use_millions = True
            val /= 1e6

    if percentage or rate:
        formatted = f"{round(val, 1):.1f}"
    elif val == 0:
        formatted = "0·00"
    else:
        power = int(np.floor(np.log10(abs(val))))
        step = 10 ** (power - 2)
        rounded = np.round(val / step) * step
        if rounded != 0:
            power = int(np.floor(np.log10(abs(rounded))))
        if power >= 2:
            dec = 0
        elif power >= 1:
            dec = 1
        elif power >= 0:
            dec = 2
        else:
            dec = 2 - power
        formatted = f"{rounded:.{dec}f}" if dec > 0 else str(int(rounded))

    formatted = formatted.replace(".", "·")
    int_part = formatted.split("·")[0].lstrip("-")
    if len(int_part) > 4:
        parts = formatted.split("·")
        integer, sign = parts[0], ""
        if integer.startswith("-"):
            sign, integer = "-", integer[1:]
        grouped = ""
        for i, digit in enumerate(reversed(integer)):
            if i > 0 and i % 3 == 0:
                grouped = " " + grouped
            grouped = digit + grouped
        formatted = sign + grouped + ("·" + parts[1] if len(parts) > 1 else "")

    if units and percentage:
        formatted += "%"
    elif units and use_billions:
        formatted += " billion"
    elif units and use_millions:
        formatted += " million"

    if small_number is not None and small_number > 0:
        if 0 < val < small_number:
            formatted = f"<{small_number}"
        elif -small_number < val < 0:
            formatted = f">-{small_number}"
    return formatted


def format_value_ui(
    mean,
    lower,
    upper,
    *,
    percentage=False,
    rate=False,
    units=True,
    nested=False,
    two_lines=False,
    small_number=None,
    separator="–",
):
    """Format ``mean (95% UI: lower-upper)`` from precomputed stats."""
    mf = smart_ui_format(
        mean, units=units, percentage=percentage, rate=rate, small_number=small_number
    )
    lf = smart_ui_format(
        lower,
        units=False,
        reference_val=mean,
        percentage=percentage,
        rate=rate,
        small_number=small_number,
    )
    uf = smart_ui_format(
        upper,
        units=False,
        reference_val=mean,
        percentage=percentage,
        rate=rate,
        small_number=small_number,
    )
    if lower < 0 < upper:
        separator = " to "
    ob, cb = ("[", "]") if nested else ("(", ")")
    if two_lines:
        return f"{mf}\n{ob}95% UI {lf}{separator}{uf}{cb}"
    return f"{mf} {ob}95% UI {lf}{separator}{uf}{cb}"
