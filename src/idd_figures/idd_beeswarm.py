import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def estimate_distance_data_units(p1, p2, s, fig, ax):
    # Calculate the distance from the edge of one point to the edge of the other in display units

    # Convert points to display coordinates
    p1_display = ax.transData.transform([p1])[0]
    p2_display = ax.transData.transform([p2])[0]

    # Calculate distance between centers in pixels
    distance_pixels = np.sqrt(
        (p2_display[0] - p1_display[0]) ** 2 + (p2_display[1] - p1_display[1]) ** 2
    )

    # Calculate radius in pixels from s
    radius_points = np.sqrt(s) / 2
    radius_pixels = radius_points * (fig.dpi / 72)

    # Distance from edge to edge = distance between centers - 2*radius
    edge_to_edge_pixels = distance_pixels - 2 * radius_pixels

    return edge_to_edge_pixels


def check_overlap(pt1, pt2, s, gap_fraction, fig, ax):
    """
    Check if two points overlap or are too close (returns True if they violate the gap requirement)
    With gap_fraction, we require edge-to-edge distance >= gap_fraction * diameter
    """
    edge_dist_pixels = estimate_distance_data_units(pt1, pt2, s, fig, ax)

    # Calculate required gap in pixels
    radius_points = np.sqrt(s) / 2
    radius_pixels = radius_points * (fig.dpi / 72)
    diameter_pixels = 2 * radius_pixels
    required_gap_pixels = gap_fraction * diameter_pixels

    # Return True if gap is violated (distance too small)
    return edge_dist_pixels < required_gap_pixels - 1e-6  # Small tolerance for floating point


def calculate_shift_for_new_point(
    new_pt, existing_points, s, gap_fraction, fig, ax, point_index, verbose_inner=True
):
    """
    Calculate the minimum horizontal shift needed for new_pt to:
    1. Maintain required gap with all existing points
    2. Be at the minimum valid distance from at least one existing point
    3. Move as little as possible
    """
    if verbose_inner:
        print(f"\n{'=' * 80}")
        print(f"PROCESSING POINT {point_index}: Original position {new_pt}")
        print(f"{'=' * 80}\n")

    # First, check if the current position is already valid (respects all gaps)
    current_is_valid = True
    violates_gap_with = []
    for idx, row in existing_points.iterrows():
        existing_pt = (row["xnew"], row["ynew"])
        if check_overlap(new_pt, existing_pt, s, gap_fraction, fig, ax):
            current_is_valid = False
            violates_gap_with.append(idx)

    if current_is_valid:
        if verbose_inner:
            print("✓ Current position is valid (all gaps satisfied). No shift needed.\n")
            print(f"{'=' * 80}\n")
        return 0

    if verbose_inner:
        print(f"✗ Current position violates gap with points: {violates_gap_with}")
        print(f"  Finding valid positions with {gap_fraction * 100:.1f}% gap...\n")

    # Convert new point to display coordinates
    new_pt_display = ax.transData.transform([new_pt])[0]

    # Calculate radius in pixels
    radius_points = np.sqrt(s) / 2
    radius_pixels = radius_points * (fig.dpi / 72)

    # Target distance between centers = 2*radius + gap
    # Gap should be gap_fraction * diameter = gap_fraction * 2 * radius
    gap_pixels = gap_fraction * 2 * radius_pixels
    target_distance_pixels = 2 * radius_pixels + gap_pixels

    all_candidates = []
    valid_shifts = []

    # For each existing point, try to find valid positions
    for idx, row in existing_points.iterrows():
        existing_pt = (row["xnew"], row["ynew"])
        existing_pt_display = ax.transData.transform([existing_pt])[0]

        # Calculate dy in display coordinates
        dy_pixels = abs(new_pt_display[1] - existing_pt_display[1])

        # Calculate required dx for target distance: sqrt(target_dist^2 - dy^2)
        dx_pixels_squared = target_distance_pixels**2 - dy_pixels**2

        if dx_pixels_squared < 0:
            # Points are too far apart vertically to achieve target distance with horizontal shift
            continue

        dx_pixels = np.sqrt(dx_pixels_squared)

        # Try both left and right of this existing point
        for sign, direction in [(1, "right"), (-1, "left")]:
            # Calculate where new point would be
            new_pt_candidate_display = np.array(
                [existing_pt_display[0] + sign * dx_pixels, new_pt_display[1]]
            )
            new_pt_candidate_data = ax.transData.inverted().transform([new_pt_candidate_display])[0]
            candidate_position = (new_pt_candidate_data[0], new_pt[1])
            shift_candidate = new_pt_candidate_data[0] - new_pt[0]

            # Check if this position violates gap with ANY OTHER existing point
            # (excluding the point we're positioned relative to)
            is_valid = True
            violates_gap_with_candidate = []
            for idx2, row2 in existing_points.iterrows():
                if idx2 == idx:
                    # Skip the point we're positioning relative to
                    continue

                existing_pt2 = (row2["xnew"], row2["ynew"])
                if check_overlap(candidate_position, existing_pt2, s, gap_fraction, fig, ax):
                    is_valid = False
                    violates_gap_with_candidate.append(idx2)

            candidate_info = {
                "relative_to_idx": idx,
                "direction": direction,
                "shift": shift_candidate,
                "abs_shift": abs(shift_candidate),
                "new_position": candidate_position,
                "is_valid": is_valid,
                "violates_gap_with": violates_gap_with_candidate,
            }

            all_candidates.append(candidate_info)

            if is_valid:
                valid_shifts.append(candidate_info)

    if verbose_inner and all_candidates:
        # Print all candidates
        print(
            f"{'Relative To':<13} {'Direction':<10} {'Shift':<12} {'|Shift|':<12} {'Valid':<8} {'Violates Gap With'}"
        )
        print(f"{'-' * 80}")
        for c in all_candidates:
            valid_str = "✓ YES" if c["is_valid"] else "✗ NO"
            violates_str = str(c["violates_gap_with"]) if c["violates_gap_with"] else "-"
            print(
                f"Point {c['relative_to_idx']:<7} {c['direction']:<10} {c['shift']:>10.4f}  {c['abs_shift']:>10.4f}  {valid_str:<8} {violates_str}"
            )

    if not valid_shifts:
        if verbose_inner:
            print("\n⚠ Warning: No valid position found! Keeping original position.")
        return None  # Return None to indicate failure

    # Sort by absolute shift and pick the smallest
    valid_shifts.sort(key=lambda x: x["abs_shift"])
    best = valid_shifts[0]

    if verbose_inner:
        print(f"\n{'=' * 80}")
        print(f"✓ CHOSEN: Shift {best['direction']} of point {best['relative_to_idx']}")
        print(f"  Shift amount: {best['shift']:.4f}")
        print(f"  Distance from original: {best['abs_shift']:.4f}")
        print(f"  New position: ({best['new_position'][0]:.4f}, {best['new_position'][1]:.4f})")
        print(f"{'=' * 80}\n")

    return best["shift"]


def position_all_points(x, y, s, gap_fraction, fig, ax, verbose_inner=True):
    """
    Position all points iteratively, processing them in order of y-coordinate:
    - Sort all points by y-coordinate
    - Keep first point (lowest y) where it is
    - For each subsequent point, shift it to maintain required gaps with all previous points

    Returns: result dataframe, max_shift_and_radius
    """

    data_coords = np.column_stack([x, y])
    display_coords = ax.transData.transform(data_coords)

    # Pre-compute radius in pixels once
    radius_points = np.sqrt(s) / 2
    radius_pixels = radius_points * (fig.dpi / 72)
    gap_pixels = gap_fraction * 2 * radius_pixels
    target_distance_pixels = 2 * radius_pixels + gap_pixels

    n_points = len(x)

    # Create dataframe with original order and positions
    data = pd.DataFrame(
        {
            "original_index": range(n_points),
            "xorig": x,
            "yorig": y,
            "xnew": [None] * n_points,
            "ynew": [None] * n_points,
            "shift": [None] * n_points,
        }
    )

    # Sort by y-coordinate (and by x as tiebreaker for stability)
    data = data.sort_values(["yorig", "xorig"]).reset_index(drop=True)
    data["processing_order"] = range(n_points)

    if verbose_inner:
        print(f"\n{'=' * 80}")
        print("PROCESSING ORDER (sorted by y-coordinate):")
        print(f"{'=' * 80}")
        print(data[["original_index", "xorig", "yorig", "processing_order"]].to_string(index=False))

    # First point stays where it is
    data.loc[0, "xnew"] = data.loc[0, "xorig"]
    data.loc[0, "ynew"] = data.loc[0, "yorig"]
    data.loc[0, "shift"] = 0.0
    if verbose_inner:
        print(f"\n{'=' * 80}")
        print(
            f"POINT {data.loc[0, 'original_index']} (processing order 0): Keeping at original position ({data.loc[0, 'xorig']:.4f}, {data.loc[0, 'yorig']:.4f})"
        )
        print(f"{'=' * 80}")

    # Process each subsequent point
    max_shift = 0.0
    for i in range(1, n_points):
        current_pt = (data.loc[i, "xorig"], data.loc[i, "yorig"])
        original_idx = data.loc[i, "original_index"]

        # Get all previously positioned points
        positioned_so_far = data[data["xnew"].notna()].copy()

        # Calculate shift needed
        shift = calculate_shift_for_new_point(
            current_pt, positioned_so_far, s, gap_fraction, fig, ax, original_idx, verbose_inner
        )

        if shift is None:
            # No valid position found - this s is too large
            return None, None

        # Apply shift
        data.loc[i, "xnew"] = data.loc[i, "xorig"] + shift
        data.loc[i, "ynew"] = data.loc[i, "yorig"]
        data.loc[i, "shift"] = shift
        max_shift = max(max_shift, abs(shift))

    # Calculate radius in data units
    radius_points = np.sqrt(s) / 2
    radius_pixels = radius_points * (fig.dpi / 72)
    # Convert radius to data units
    origin_display = ax.transData.transform([(0, 0)])[0]
    radius_offset_display = origin_display + np.array([radius_pixels, 0])
    radius_data = ax.transData.inverted().transform([radius_offset_display])[0]
    radius_in_data_units = abs(radius_data[0])

    # Maximum extent from original position
    max_shift_and_radius = max_shift + radius_in_data_units

    # Sort back to original order for output
    result = data.sort_values("original_index").reset_index(drop=True)

    return result, max_shift_and_radius


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
    verbose_optim_min=True,
    verbose_optim_full=True,
    verbose_inner=False,
    s_min=100,
    s_max=10000,
):
    """
    Find the largest s such that all points can be positioned within margin of their original x-coordinate.
    Margin constraint: |shift| + radius <= margin for all points
    """
    if verbose_optim_full:
        print(f"\n{'#' * 80}")
        print(f"# FINDING OPTIMAL s WITH MARGIN = {margin}")
        print(f"{'#' * 80}\n")

    # Binary search for optimal s
    best_s = None
    best_result = None

    # history of tests
    history = []

    seq_errors = []
    best_error = None
    max_seq_error = float("inf")
    iteration = 0
    while True:
        iteration += 1
        s_test = (s_min + s_max) / 2

        if verbose_optim_full:
            print(f"\n{'=' * 80}")
            print(
                f"ITERATION {iteration}: Testing s = {s_test:.1f} (range: [{s_min:.1f}, {s_max:.1f}])"
            )
            print(f"{'=' * 80}")

        if verbose_optim_min:
            print(f"Iteration {iteration}: Testing s = {s_test:.1f}.")

        # Try positioning with this s
        result, max_shift_and_radius = position_all_points(
            x, y, s_test, gap_fraction, fig, ax, verbose_inner=verbose_inner
        )

        # derive max_shift if result provides per-point shifts
        max_shift = None
        if result is not None and "shift" in result.columns:
            try:
                max_shift = float(result["shift"].abs().max())
            except Exception:
                max_shift = None

        if result is None:
            valid = False
            # Failed to position - s is too large
            if verbose_optim_min:
                print("   Result: ❌ FAILED: Could not position all points (s too large)")
            s_max = s_test
        elif max_shift_and_radius > margin:
            # Positioned but exceeds margin - s is too large
            valid = False
            if verbose_optim_min:
                print(
                    f"   Iteration {iteration}: Testing s = {s_test:.1f}. Result: ❌ FAILED: Max shift+radius = {max_shift_and_radius:.4f} > margin {margin:.4f}"
                )
            s_max = s_test
        else:
            valid = True
            # Success! Try larger s
            if verbose_optim_min:
                print(
                    f"   Iteration {iteration}: Testing s = {s_test:.1f}. Result: ✅ SUCCESS: Max shift+radius = {max_shift_and_radius:.4f} <= margin {margin:.4f}"
                )
                print(f"   Current best error: {best_error}.")
            best_s = s_test
            best_result = result
            s_min = s_test

        error = abs(margin - max_shift_and_radius)
        if best_error is None or (error < best_error and valid):
            best_error = error
            seq_errors.append(error)
            if len(seq_errors) > N_seq:
                seq_errors = seq_errors[-N_seq:]
                seq_error_diff = [val - seq_errors[-1] for val in seq_errors[:-1]]
                max_seq_error = np.max(np.abs(seq_error_diff))

        # record test outcome
        history.append(
            {
                "iteration": iteration,
                "s_test": s_test,
                "error": error,
                "max_seq_error": max_seq_error,
                "valid": valid,
                "max_shift_and_radius": max_shift_and_radius,
                "max_shift": max_shift,
            }
        )
        # Stopping conditions
        if iteration >= max_iterations:
            break
        if error < tol and valid:
            break
        if max_seq_error < tol_seq and iteration > 15:
            break

    if verbose_optim_full:
        print(f"Tolerance check: error={error}, tol={tol}, valid={valid}, iterations={iteration}")
        print(f"Is iterations >= max_iterations? {iteration >= max_iterations}")
        print(f"Is error < tol? {error < tol}")
        print(f"Is the result valid? {valid}")
        print(
            f"Is max_seq_error < tol_seq? {max_seq_error < tol_seq} (max_seq_error={max_seq_error}, tol_seq={tol_seq})"
        )
        if max_seq_error < tol_seq and iteration > 15:
            print(f"Seq error values (last {N_seq}): {seq_errors}")
            print(f"Seq error diffs: {[val - seq_errors[-1] for val in seq_errors[:-1]]}")
            print(f"Max seq error: {max_seq_error}")

    if best_s is None:
        print(f"\n⚠️  WARNING: Could not find valid s within range. Using minimum s = {s_min:.1f}")
        best_s = s_min
        best_result, _ = position_all_points(
            x, y, best_s, gap_fraction, fig, ax, verbose_inner=verbose_inner
        )

    if verbose_optim_full:
        print(f"\n{'#' * 80}")
        print(f"# OPTIMAL s FOUND: {best_s:.1f}")
        print(f"{'#' * 80}\n")

        # Run one more time with verbose output
        print(f"\n{'=' * 80}")
        print(f"FINAL POSITIONING WITH s = {best_s:.1f}")
        print(f"{'=' * 80}")
    final_result, max_extent = position_all_points(
        x, y, best_s, gap_fraction, fig, ax, verbose_inner=verbose_inner
    )

    # attach history to the function for later inspection and print compact summary
    find_optimal_s.history = history
    if verbose_optim_full:
        print("\nTest history (s_test, success, max_shift_and_radius, max_shift):")
        for h in history:
            print(
                f"  {h['s_test']:10.1f}  {h['success']!s:5}  {h['max_shift_and_radius']!s:>10}  {h['max_shift']!s:>8}"
            )

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
):

    # Handle figure and axis creation
    if ax is None:
        fig, ax = plt.subplots(figsize=fig_size)
        show_plot = True
    else:
        show_plot = False
        if fig is None:
            fig = ax.get_figure()

    # Extract x and y data
    y = data[y_var].values
    if x_var_order is None:
        x_var_order = data[x_var].unique()
    # Map x_var to numeric positions based on order
    x_mapping = {val: idx for idx, val in enumerate(x_var_order)}
    x = data[x_var].map(x_mapping).values

    # Set y-limits
    if ylim is not None:
        ax.set_ylim(ylim)
    else:
        y_diff = max(y) - min(y)
        ax.set_ylim(min(y) - ylim_stretch * y_diff, max(y) + ylim_stretch * y_diff)
    # Set x-limits wide enough to accommodate shifts
    ax.set_xlim(min(x) - margin - x_edge_pad, max(x) + margin + x_edge_pad)

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
    )

    final_data = data.join(final_positions[["xnew", "ynew"]])

    # Get unique x positions to draw margin lines
    unique_x = sorted(set(x))

    # Draw margin lines for each unique x position
    if draw_margin:
        for x_pos in unique_x:
            ax.axvline(x=x_pos - margin, color="gray", linestyle=":", linewidth=2)
            ax.axvline(x=x_pos + margin, color="gray", linestyle=":", linewidth=2)
            ax.axvline(x=x_pos, color="gray", linestyle="-", linewidth=0.5, alpha=0.3)

    # Plot final positions (bold) with dynamic colors
    for i, row in final_data.iterrows():
        color = color_dict[row[color_var]]
        ax.scatter(
            [row["xnew"]],
            [row["ynew"]],
            s=optimal_s,
            edgecolors=None,
            facecolors=color,
            marker="o",
            linewidths=2,
        )

    ax.set_xticks(list(x_mapping.values()))
    ax.set_xticklabels(list(x_mapping.keys()))
    ax.set_xlabel("")

    plt.show()
