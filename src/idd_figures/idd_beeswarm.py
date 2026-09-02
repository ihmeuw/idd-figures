"""Auto-sizing beeswarm for matplotlib: the plotting wrapper around
``idd_figures.beeswarm_core``.

The layout algorithms (greedy min-shift swarm, processing orders, phi-penalized
value moves, spine-drop, R-beeswarm grids) live in ``beeswarm_core`` in a
dimensionless space where the collision diameter is 1. This module is the
matplotlib unit supplier (extraction step 1, 2026-09-02): it turns a scatter
size ``s`` (points^2, plus the SCATTER_LW stroke, plus ``gap_fraction``) into a
collision diameter in pixels, divides by the axes' pixels-per-data-unit on
each axis to get the diameter in category units and value units, hands those
to the core, and converts the core's chosen diameter back to ``s``. The
resulting layouts are the same as the 2026-08-31 pixel-space implementation
(verified by parity against it); ``find_optimal_s`` now bisects the diameter
rather than ``s``, so the converged ``s`` can differ within its tolerance.

Orientation and sidedness: ``orient="v"`` (default) draws categories on x and
values on y with horizontal offsets; ``orient="h"`` draws values on x and
categories on y with vertical offsets. ``one_sided=True`` restricts offsets to
the positive side of the category line (right for "v", up for "h").

The layout is computed for the axes state at call time. Resizing the figure,
``tight_layout``, or ``bbox_inches="tight"`` afterwards changes the data-to-
pixel transform and invalidates the packing; set the axes up first.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.markers import MarkerStyle

from idd_figures.beeswarm_core import Gravity, find_optimal_size, layout  # noqa: F401
from idd_figures.beeswarm_shapes import CIRCLE, PolygonShape, _dedupe_closed, offset_polygon

SCATTER_LW = 2.0  # linewidth (points) of the drawn dots; the stroke straddles
# the marker path, so the VISUAL diameter is sqrt(s) + SCATTER_LW points. The
# layout must use that (2026-08-31 fix: gap_fraction=0.1 dots drew touching).


def visual_diameter_px(s, dpi, gap_fraction=0.0):
    """Collision diameter, in pixels, of a scatter dot of size ``s`` (points^2)
    drawn with the SCATTER_LW stroke, times ``1 + gap_fraction``."""
    return (np.sqrt(s) + SCATTER_LW) * dpi / 72.0 * (1.0 + gap_fraction)


def marker_size_from_diameter_px(d_px, dpi, gap_fraction=0.0):
    """Inverse of ``visual_diameter_px``: the scatter ``s`` whose stroked dot has
    collision diameter ``d_px``. Diameters smaller than the stroke alone map
    to ``s = 0``."""
    root = d_px / (1.0 + gap_fraction) * 72.0 / dpi - SCATTER_LW
    return float(max(root, 0.0) ** 2)


def marker_vertices_px(marker, s, dpi, linewidth=SCATTER_LW):
    """Outline of a filled scatter marker, in pixels about its centre.

    The marker path is scaled exactly as ``Axes.scatter`` scales it (the
    marker's own transform, then sqrt(s) points), flattened to a polygon, and
    dilated by half the stroke width with mitered joins (``offset_polygon``),
    since the stroke straddles the path. Productionized from
    ``notebooks/idd_beeswarm/point_distance.ipynb::get_marker_geometry``,
    which returned data coordinates and needed a live axes; this needs only
    the dpi. Markers without an interior ('+', 'x', '|', '_') raise.
    """
    ms = MarkerStyle(marker)
    transform = ms.get_transform().scale(np.sqrt(s) * dpi / 72.0)
    polys = transform.transform_path(ms.get_path()).to_polygons()
    if len(polys) != 1:
        msg = f"marker {marker!r} does not flatten to one filled polygon ({len(polys)} found)"
        raise ValueError(msg)
    V = _dedupe_closed(np.asarray(polys[0], dtype=float))
    return offset_polygon(V, linewidth / 2.0 * dpi / 72.0) if linewidth else V


def marker_shape(marker, s, dpi, gap_fraction=0.0, mode="hull", orient="v"):
    """Collision shape of scatter marker ``marker`` at size ``s``, in the core's
    D units: D is the stroked CIRCLE's collision diameter at this ``s``
    (``visual_diameter_px``), so 'o' is exactly the unit disk and every other
    mark is scaled consistently with it. The gap is a uniform dilation about
    the centre, as for circles. ``mode`` is "hull" or "decompose" for
    non-convex marks ('*', 'P', 'X'); convex marks are one piece regardless.
    The core's first coordinate is the CATEGORY axis: for ``orient="h"`` the
    outline is transposed from plot (x, y) into (category, value).
    """
    if marker == "o":
        return CIRCLE
    V = marker_vertices_px(marker, s, dpi) * (1.0 + gap_fraction)
    if orient == "h":
        V = V[:, ::-1]
    return PolygonShape(V / visual_diameter_px(s, dpi, gap_fraction), mode=mode)


def _px_per_unit(ax, orient):
    """Signed pixels per data unit along the category axis and the value axis."""
    origin = ax.transData.transform([(0.0, 0.0)])[0]
    ux = ax.transData.transform([(1.0, 0.0)])[0][0] - origin[0]
    uy = ax.transData.transform([(0.0, 1.0)])[0][1] - origin[1]
    if orient == "v":
        return ux, uy  # categories on plot-x, values on plot-y
    if orient == "h":
        return uy, ux  # categories on plot-y, values on plot-x
    msg = f"orient must be 'v' or 'h', got {orient!r}"
    raise ValueError(msg)


def _value_frame(ax, orient):
    return ax.get_ylim() if orient == "v" else ax.get_xlim()


def _result_frame(x, y, cat_new, val_new, orient):
    """The layout as the historical result DataFrame, in PLOT coordinates."""
    return pd.DataFrame(
        {
            "original_index": np.arange(x.size),
            "xorig": x,
            "yorig": y,
            "xnew": cat_new if orient == "v" else val_new,
            "ynew": val_new if orient == "v" else cat_new,
            "shift": cat_new - x,
        }
    )


def position_all_points(
    x,
    y,
    s,
    gap_fraction,
    fig,
    ax,
    verbose_inner=False,
    orient="v",
    one_sided=False,
    process_order="ascending",
    bin_order="middle-out",
    method="swarm",
    phi=None,
    marker="o",
    shape_mode="hull",
    backend="auto",
    gravity=None,
):
    """Lay out one dot size: returns (result df, max |offset| + radius), or
    (None, None) if some point has no valid position at this ``s``.

    ``x`` is the category coordinate, ``y`` the value, whatever the orient;
    the returned ``xnew``/``ynew`` are PLOT coordinates (for "h" the value
    lands on the plot x-axis and the offset category coordinate on plot y).
    ``method``, ``process_order``, ``bin_order``, ``one_sided``, ``phi`` are
    documented on ``beeswarm_core.layout`` and the engines it dispatches to.
    ``marker`` is the scatter marker the dots will be drawn with and
    ``shape_mode`` ("hull" / "decompose") how a non-convex one is packed
    (``marker_shape``); non-circle markers support the swarm method only.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ux, uy = _px_per_unit(ax, orient)
    d_px = visual_diameter_px(s, fig.dpi, gap_fraction)
    out = layout(
        x,
        y,
        d_px / ux,
        d_px / uy,
        method=method,
        process_order=process_order,
        bin_order=bin_order,
        one_sided=one_sided,
        phi=phi,
        val_frame=_value_frame(ax, orient),
        gap_fraction=gap_fraction,
        shape=marker_shape(marker, s, fig.dpi, gap_fraction, shape_mode, orient),
    backend=backend,
    gravity=gravity,
    )
    if out is None:
        return None, None
    cat_new, val_new, extent = out
    return _result_frame(x, y, cat_new, val_new, orient), extent


def find_optimal_s(
    x,
    y,
    gap_fraction,
    margin,
    fig,
    ax,
    tol=1e-4,
    N_seq=5,
    tol_seq=1e-4,
    max_iterations=50,
    verbose_optim_min=False,
    verbose_optim_full=False,
    verbose_inner=False,
    s_min=100,
    s_max=10000,
    orient="v",
    one_sided=False,
    process_order="ascending",
    bin_order="middle-out",
    method="swarm",
    phi=None,
    marker="o",
    shape_mode="hull",
    backend="auto",
    gravity=None,
):
    """Largest ``s`` whose max |offset| + radius fits in ``margin``.

    The search runs in the core over the collision diameter in pixels between
    the diameters of ``s_min`` and ``s_max``; the result is converted back to
    ``s``. Returns (best_s, result df, max_extent, history); ``result df`` is
    None if no size in range was valid (the core warns). History entries
    carry both ``d_test`` (pixels) and ``s_test``.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ux, uy = _px_per_unit(ax, orient)

    def shape_at(d_px):  # the stroke is not proportional to s: rebuild per size
        s_d = marker_size_from_diameter_px(d_px, fig.dpi, gap_fraction)
        return marker_shape(marker, s_d, fig.dpi, gap_fraction, shape_mode, orient)

    best_d, final, history = find_optimal_size(
        x,
        y,
        margin,
        1.0 / ux,
        1.0 / uy,
        visual_diameter_px(s_min, fig.dpi, gap_fraction),
        visual_diameter_px(s_max, fig.dpi, gap_fraction),
        gap_fraction=gap_fraction,
        tol=tol,
        N_seq=N_seq,
        tol_seq=tol_seq,
        max_iterations=max_iterations,
        verbose=verbose_optim_min,
        method=method,
        process_order=process_order,
        bin_order=bin_order,
        one_sided=one_sided,
        phi=phi,
        val_frame=_value_frame(ax, orient),
        shape=CIRCLE if marker == "o" else shape_at,
    backend=backend,
    gravity=gravity,
    )
    for h in history:
        h["s_test"] = marker_size_from_diameter_px(h["d_test"], fig.dpi, gap_fraction)
    best_s = marker_size_from_diameter_px(best_d, fig.dpi, gap_fraction)
    if final is None:
        return best_s, None, None, history
    cat_new, val_new, extent = final
    return best_s, _result_frame(x, y, cat_new, val_new, orient), extent, history


def idd_beeswarm(
    data,
    x_var,
    y_var,
    color_var,
    color_dict,
    x_var_order=None,
    ax=None,
    fig=None,
    fig_size=(8, 8),
    ylim=None,
    ylim_stretch=0.2,
    gap_fraction=0.1,
    margin=0.5,
    x_edge_pad=0.5,
    tol=1e-4,
    N_seq=5,
    tol_seq=1e-4,
    max_iterations=50,
    draw_margin=False,
    verbose_optim_min=False,
    verbose_optim_full=False,
    verbose_inner=False,
    s_min=100,
    s_max=10000,
    orient="v",
    one_sided=False,
    process_order="ascending",
    bin_order="middle-out",
    method="swarm",
    phi=None,
    marker="o",
    shape_mode="hull",
    backend="auto",
    gravity=None,
):
    """Auto-sized beeswarm of ``y_var`` per ``x_var`` category.

    ``orient="v"``: categories on plot-x, values on plot-y (the original).
    ``orient="h"``: values on plot-x, categories on plot-y.
    ``one_sided=True``: offsets only on the positive side of the category
    line (right for "v", up for "h"); the unused side keeps a small pad.
    ``method``: "swarm" (the greedy, value-exact layout; everything below
    applies to it) or the R-beeswarm deterministic grids "center", "hex",
    "square" (see ``beeswarm_core._grid_layout``), which QUANTIZE values to
    row centers and ignore ``process_order``/``bin_order``.
    ``phi`` (swarm only, > 0): allow a colliding dot to move along the VALUE
    axis too, choosing the position minimizing doff^2 + phi * dval^2; larger
    phi keeps values truer; ties keep the value-exact move; None (default)
    forbids value moves entirely. Avoid tiny phi (the search widens as
    1/sqrt(phi)).
    ``process_order``: "ascending" (the original), "descending",
    "middle-out", "spine" (pack the category line with every no-shift point
    first, then fill the gaps bin by bin; see ``_spine_bin_order``),
    "spine-drop" (spine first, then each bin repeatedly places whichever of
    its points lands lowest; no value wiggle without ``phi``), or an
    explicit permutation of ``range(n)`` (row positions in ``data``) giving
    the placement order directly. ``bin_order`` ("middle-out", "ascending",
    "descending") sets how "spine"/"spine-drop" walk the bins; ignored
    otherwise.
    ``ylim``/``ylim_stretch`` always describe the VALUE axis, ``margin``/
    ``x_edge_pad`` the category axis, whatever the orientation.
    ``marker``: any filled scatter marker; non-circles are packed by their
    actual outline (swarm method only, no phi). ``shape_mode`` "hull" packs a
    non-convex marker ('*', 'P', 'X') by its convex hull; "decompose" packs
    it exactly. See ``marker_shape``.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=fig_size)
    elif fig is None:
        fig = ax.get_figure()

    y = data[y_var].values
    if x_var_order is None:
        x_var_order = data[x_var].unique()
    x_mapping = {val: idx for idx, val in enumerate(x_var_order)}
    x = data[x_var].map(x_mapping).values

    if ylim is None:
        y_diff = max(y) - min(y)
        ylim = (min(y) - ylim_stretch * y_diff, max(y) + ylim_stretch * y_diff)
    lo_pad = 0.15 if one_sided else margin + x_edge_pad  # unused side stays slim
    cat_lim = (min(x) - lo_pad, max(x) + margin + x_edge_pad)
    if orient == "v":
        ax.set_ylim(ylim)
        ax.set_xlim(cat_lim)
    else:
        ax.set_xlim(ylim)
        ax.set_ylim(cat_lim)

    optimal_s, final_positions, max_extent, history = find_optimal_s(
        x,
        y,
        gap_fraction,
        margin,
        fig,
        ax,
        tol=tol,
        N_seq=N_seq,
        tol_seq=tol_seq,
        max_iterations=max_iterations,
        verbose_optim_min=verbose_optim_min,
        verbose_optim_full=verbose_optim_full,
        verbose_inner=verbose_inner,
        s_min=s_min,
        s_max=s_max,
        orient=orient,
        one_sided=one_sided,
        process_order=process_order,
        bin_order=bin_order,
        method=method,
        phi=phi,
        marker=marker,
        shape_mode=shape_mode,
    backend=backend,
    gravity=gravity,
    )

    final_data = data.join(final_positions[["xnew", "ynew"]])

    if draw_margin:
        line = ax.axvline if orient == "v" else ax.axhline
        for x_pos in sorted(set(x)):
            if not one_sided:
                line(x_pos - margin, color="gray", linestyle=":", linewidth=2)
            line(x_pos + margin, color="gray", linestyle=":", linewidth=2)
            line(x_pos, color="gray", linestyle="-", linewidth=0.5, alpha=0.3)

    for level, sub in final_data.groupby(color_var, sort=False):
        ax.scatter(
            sub["xnew"],
            sub["ynew"],
            s=optimal_s,
            marker=marker,
            facecolors=color_dict[level],
            edgecolors=None,
            linewidths=SCATTER_LW,
        )

    ticks, labels = list(x_mapping.values()), list(x_mapping.keys())
    if orient == "v":
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels)
        ax.set_xlabel("")
    else:
        ax.set_yticks(ticks)
        ax.set_yticklabels(labels)
        ax.set_ylabel("")

    plt.show()
