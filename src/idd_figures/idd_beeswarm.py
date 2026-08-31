"""Auto-sizing beeswarm: greedy min-shift layout, dot size optimized to margin.

Points are processed in value order; each takes the smallest offset (along the
category axis) that keeps every pair of dot centers at least one diameter
(plus ``gap_fraction`` of a diameter) apart, measured in pixels;
``find_optimal_s`` binary-searches the largest dot size whose
max |offset| + radius stays within ``margin`` category-axis units.

Orientation and sidedness (2026-08-28): ``orient="v"`` (default) draws
categories on x and values on y with horizontal offsets — the original
behavior, bit-identical layouts; ``orient="h"`` draws values on x and
categories on y with vertical offsets. ``one_sided=True`` restricts offsets to
the positive side of the category line (right for "v", up for "h").

Vectorized rewrite (2026-08-28): identical algorithm, API, and defaults to the
original implementation, ~1000x faster per layout (one transData.transform for
all points, numpy collision math over the window of possibly-colliding
neighbours, per-colour scatter). Layouts are bit-identical to the original
except at exact mirror ties (a point tangent left or right of its anchor with
equal |shift|), where this version deterministically picks the positive side;
either choice is a valid, overlap-free swarm.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TOL_PX = 1e-6  # the original's collision tolerance, in pixels


def _layout_px(off_px, val_px, order, D, one_sided=False):
    """Greedy min-shift swarm in pixel space.

    ``off_px`` is the offset axis (dots slide along it), ``val_px`` the value
    axis (fixed). Returns new offset-axis positions, or None if some point has
    no valid position (s too large). ``order`` is the processing order; the
    first point stays put, every later one takes the smallest |shift| —
    smallest non-negative shift when ``one_sided`` — that keeps all center
    distances >= D (within TOL_PX).
    """
    n = off_px.size
    out = off_px.copy()
    PA = np.empty(n)
    PB = np.empty(n)
    k = 0
    thresh2 = (D - TOL_PX) ** 2
    for i in order:
        ai, bi = off_px[i], val_px[i]
        if k:
            dv = PB[:k] - bi
            near = np.abs(dv) < D
            if near.any():
                na, ndv = PA[:k][near], dv[near]
                if ((na - ai) ** 2 + ndv * ndv < thresh2).any():
                    da = np.sqrt(D * D - ndv * ndv)
                    cands = np.concatenate([na + da, na - da])
                    d2 = (cands[:, None] - na[None, :]) ** 2 + (ndv * ndv)[None, :]
                    ok = (d2 >= thresh2).all(axis=1)
                    valid = cands[ok]
                    if one_sided:
                        valid = valid[valid >= off_px[i] - TOL_PX]
                    if valid.size == 0:
                        return None
                    ai = valid[np.argmin(np.abs(valid - ai))]
        PA[k], PB[k] = ai, bi
        k += 1
        out[i] = ai
    return out


def position_all_points(
    x, y, s, gap_fraction, fig, ax, verbose_inner=False, orient="v", one_sided=False
):
    """Lay out one dot size: returns (result df, max |offset| + radius).

    ``x`` is the category coordinate, ``y`` the value, whatever the orient;
    the returned ``xnew``/``ynew`` are PLOT coordinates (for "h" the value
    lands on the plot x-axis and the offset category coordinate on plot y).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if orient == "v":
        pts = ax.transData.transform(np.column_stack([x, y]))
        off_px, val_px = pts[:, 0], pts[:, 1]
        unit = ax.transData.transform([(1.0, 0.0)])[0][0] - ax.transData.transform([(0.0, 0.0)])[0][0]
    elif orient == "h":
        pts = ax.transData.transform(np.column_stack([y, x]))  # plot coords: (value, cat)
        off_px, val_px = pts[:, 1], pts[:, 0]
        unit = ax.transData.transform([(0.0, 1.0)])[0][1] - ax.transData.transform([(0.0, 0.0)])[0][1]
    else:
        msg = f"orient must be 'v' or 'h', got {orient!r}"
        raise ValueError(msg)

    r_px = np.sqrt(s) / 2.0 * fig.dpi / 72.0
    D = 2.0 * r_px * (1.0 + gap_fraction)

    order = np.lexsort((x, y))          # by value, category as tiebreak
    new_px = _layout_px(off_px, val_px, order, D, one_sided=one_sided)
    if new_px is None:
        return None, None

    shift = (new_px - off_px) / unit
    cat_new = x + shift
    result = pd.DataFrame(
        {
            "original_index": np.arange(x.size),
            "xorig": x,
            "yorig": y,
            "xnew": cat_new if orient == "v" else y,
            "ynew": y if orient == "v" else cat_new,
            "shift": shift,
        }
    )
    return result, float(np.abs(shift).max() + r_px / abs(unit))


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
):
    """Binary-search the largest s whose max |offset| + radius fits in margin."""
    best_s = None
    history = []
    seq_errors: list[float] = []
    best_error = None
    max_seq_error = float("inf")
    iteration = 0
    while True:
        iteration += 1
        s_test = (s_min + s_max) / 2.0
        result, extent = position_all_points(
            x, y, s_test, gap_fraction, fig, ax, orient=orient, one_sided=one_sided
        )
        if result is None:
            valid = False
            s_max = s_test
            error = float("inf")
        elif extent > margin:
            valid = False
            s_max = s_test
            error = abs(margin - extent)
        else:
            valid = True
            best_s = s_test
            s_min = s_test
            error = abs(margin - extent)
        if verbose_optim_min:
            print(f"Iteration {iteration}: s = {s_test:.1f} "
                  f"{'ok' if valid else 'fail'} (extent {extent})")
        if valid and (best_error is None or error < best_error):
            best_error = error
            seq_errors.append(error)
            if len(seq_errors) > N_seq:
                seq_errors = seq_errors[-N_seq:]
                max_seq_error = float(np.max(np.abs(
                    [v - seq_errors[-1] for v in seq_errors[:-1]])))
        history.append({"iteration": iteration, "s_test": s_test, "valid": valid,
                        "max_shift_and_radius": extent, "error": error})
        if iteration >= max_iterations:
            break
        if valid and error < tol:
            break
        if max_seq_error < tol_seq and iteration > 15:
            break

    if best_s is None:
        print(f"\n⚠️  WARNING: Could not find valid s within range. "
              f"Using minimum s = {s_min:.1f}")
        best_s = s_min
    final_result, max_extent = position_all_points(
        x, y, best_s, gap_fraction, fig, ax, orient=orient, one_sided=one_sided
    )
    find_optimal_s.history = history
    return best_s, final_result, max_extent, history


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
):
    """Auto-sized beeswarm of ``y_var`` per ``x_var`` category.

    ``orient="v"``: categories on plot-x, values on plot-y (the original).
    ``orient="h"``: values on plot-x, categories on plot-y.
    ``one_sided=True``: offsets only on the positive side of the category
    line (right for "v", up for "h"); the unused side keeps a small pad.
    ``ylim``/``ylim_stretch`` always describe the VALUE axis, ``margin``/
    ``x_edge_pad`` the category axis, whatever the orientation.
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
    lo_pad = 0.15 if one_sided else margin + x_edge_pad   # unused side stays slim
    cat_lim = (min(x) - lo_pad, max(x) + margin + x_edge_pad)
    if orient == "v":
        ax.set_ylim(ylim)
        ax.set_xlim(cat_lim)
    else:
        ax.set_xlim(ylim)
        ax.set_ylim(cat_lim)

    optimal_s, final_positions, max_extent, history = find_optimal_s(
        x, y, gap_fraction, margin, fig, ax,
        tol=tol, N_seq=N_seq, tol_seq=tol_seq, max_iterations=max_iterations,
        verbose_optim_min=verbose_optim_min, verbose_optim_full=verbose_optim_full,
        verbose_inner=verbose_inner, s_min=s_min, s_max=s_max,
        orient=orient, one_sided=one_sided,
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
        ax.scatter(sub["xnew"], sub["ynew"], s=optimal_s, marker="o",
                   facecolors=color_dict[level], edgecolors=None, linewidths=2)

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
