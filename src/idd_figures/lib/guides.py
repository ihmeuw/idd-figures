"""Executable anatomy guides: figures that document the library's own knobs.

Each ``guide_*`` function renders a real layout and annotates it with the
KWARG NAMES and LIVE VALUES that control each space, band, and text — the
matplotlib/idd-figures analogue of R's annotated ``par()`` margin diagram.
Because every number is read from the actual call (or measured from realised
axes positions), the guides cannot drift from the truth.

Pure-matplotlib guides import nothing geo; the two map guides import the geo
stack lazily. The vignette notebook imports these functions (import-only rule).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

from idd_figures.lib.layouts.grids import cell, grid, paint, panel_grid

__all__ = [
    "guide_bar_cell_anatomy",
    "guide_coordinate_frames",
    "guide_grid_anatomy",
    "guide_map_facet_anatomy",
    "guide_map_panel_anatomy",
    "guide_text_placement",
    "guide_text_styles",
]

_INK = "#d81b60"  # annotation colour, distinct from any data colour used here
_BOX = {"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.9}


def _arrow(fig, p0, p1, label, *, rotation=0, fontsize=9, dx=0.0, dy=0.0):
    """Double-headed arrow between figure-fraction points + a boxed label."""
    fig.add_artist(FancyArrowPatch(p0, p1, arrowstyle="<->", mutation_scale=10,
                                   color=_INK, lw=1.1, transform=fig.transFigure,
                                   zorder=1000, shrinkA=0, shrinkB=0))
    if not label:
        return
    mx, my = (p0[0] + p1[0]) / 2 + dx, (p0[1] + p1[1]) / 2 + dy
    fig.text(mx, my, label, color=_INK, fontsize=fontsize, ha="center", va="center",
             rotation=rotation, bbox=_BOX, zorder=1001)


def _note(fig, y, text, *, fontsize=9):
    fig.text(0.02, y, text, fontsize=fontsize, color="0.25", ha="left", va="bottom")


def _outline_cells(fig, *, color="0.45"):
    """Dashed outline of every axes' ALLOCATED cell box — the grid's invisible truth.

    The dimension arrows in these guides measure CELL edges. Bar/legend cells
    inset their drawn ink, so without these outlines an arrow can appear to end
    in empty space; with them, every arrow endpoint lands on a visible edge.
    """
    from matplotlib.patches import Rectangle

    for ax in fig.axes:
        p = ax.get_position(original=True)
        fig.add_artist(Rectangle((p.x0, p.y0), p.width, p.height, fill=False,
                                 edgecolor=color, lw=0.8, ls=(0, (3, 3)),
                                 transform=fig.transFigure, zorder=999))


def _empty(ax, _data=None):
    ax.set_xticks([])
    ax.set_yticks([])


def _pos(fig, name):
    return fig.axes_by_name[name].get_position(original=True)


def guide_grid_anatomy(*, margins=None, wspace=0.30, hspace=0.40,
                       height_ratios=(2, 1), width_ratios=(1, 2), figsize=(9, 6.5),
                       notes=True, cell_boxes=True):
    """panel_grid: margins / wspace / hspace / ratios, each labelled in place.

    Every knob is a parameter and every annotation reads the live value — call
    again with different numbers and the diagram re-annotates itself. That IS
    the changed-version mechanism (vignette shows a default + a changed call).
    """
    margins = {"left": 0.10, "right": 0.94, "top": 0.88, "bottom": 0.14} if margins is None else margins
    hr, wr = list(height_ratios), list(width_ratios)
    spec = grid((2, 2), [
        cell((0, 0), paint(_empty, None), name="r0c0"),
        cell((0, 1), paint(_empty, None), name="r0c1"),
        cell((1, 0), paint(_empty, None), name="r1c0"),
        cell((1, 1), paint(_empty, None), name="r1c1"),
    ], height_ratios=hr, width_ratios=wr, margins=margins, wspace=wspace, hspace=hspace)
    fig = panel_grid(spec, figsize=figsize)

    a, b, c = _pos(fig, "r0c0"), _pos(fig, "r0c1"), _pos(fig, "r1c0")
    ymid, xmid = (a.y0 + a.y1) / 2, (a.x0 + a.x1) / 2
    _arrow(fig, (0.0, ymid), (a.x0, ymid), f'margins["left"] = {margins["left"]}', dx=0.075, dy=0.03)
    _arrow(fig, (b.x1, ymid), (1.0, ymid), f'margins["right"] = {margins["right"]}', dx=-0.075, dy=0.03)
    _arrow(fig, (xmid, a.y1), (xmid, 1.0), f'margins["top"] = {margins["top"]}', dx=0.14)
    _arrow(fig, (0.70, 0.0), (0.70, c.y0), f'margins["bottom"] = {margins["bottom"]}', dx=0.0, dy=0.035)
    _arrow(fig, (a.x1, ymid), (b.x0, ymid), f"wspace = {wspace}\n(x mean panel width)", dy=0.06)
    _arrow(fig, ((c.x0 + c.x1) / 2, c.y1), ((c.x0 + c.x1) / 2, a.y0),
           f"hspace = {hspace}\n(x mean panel height)", dx=0.16)
    fig.text(a.x0 + 0.01, a.y0 + 0.01, f"height_ratios = {hr}\nwidth_ratios = {wr}",
             fontsize=9, color=_INK, ha="left", va="bottom", bbox=_BOX)
    if notes:
        _note(fig, 0.045, "Ratios split the area INSIDE the margins; gaps are charged against the\n"
                          "MEAN panel size (geometry.gap_factor inverts this).", fontsize=8)
        _note(fig, 0.005, "Nested grids have NO margins of their own — the parent's cell IS the\n"
                          "margin control (spacer rows/cols if needed).", fontsize=8)
    if cell_boxes:
        _outline_cells(fig)
    return fig


def guide_map_panel_anatomy(*, extent=(0, 6, 0, 4), fig_width=8.0, title_h=0.5,
                            legend_h=0.75, legend_title_h=0.25, cell_boxes=True):
    """map_panel: the four stacked bands and the derived (never chosen) map height.

    Parameters are the real map_panel knobs; annotations read live values, so a
    changed call (e.g. a square extent, a taller title band) IS the changed guide.
    """
    from idd_figures.lib.colors import binned_colormap
    from idd_figures.lib.layouts.maps import map_panel
    cmap, norm, colors = binned_colormap([0, 50, 100])
    fig = map_panel(extent=extent, cmap=cmap, norm=norm, colors=colors, ocean=False,
                    draw_data=False, title="title", legend_title="legend_title",
                    fig_width=fig_width, title_h=title_h, legend_h=legend_h,
                    legend_title_h=legend_title_h)
    fh = fig.get_size_inches()[1]
    map_h = fig_width * (extent[3] - extent[2]) / (extent[1] - extent[0])

    bands = [  # creation order: title / map / legend / legend-title
        (f'title_h = {title_h}"', fig.axes[0]),
        (f'map row = fig_width x aspect = {map_h:.2f}" (DERIVED)', fig.axes[1]),
        (f'legend_h = {legend_h}"', fig.axes[2]),
        (f'legend_title_h = {legend_title_h}"', fig.axes[3]),
    ]
    for label, ax in bands:  # arrow at the left edge, horizontal label beside it
        p = ax.get_position(original=True)
        _arrow(fig, (0.012, p.y0), (0.012, p.y1), "")
        fig.text(0.028, (p.y0 + p.y1) / 2, label, color=_INK, fontsize=8,
                 ha="left", va="center", bbox=_BOX, zorder=1001)
    map_p = fig.axes[1].get_position(original=True)
    fig.text(0.05, map_p.y0 + 0.02, 'aspect is EXPLICIT (set_aspect(1.0, "box")):\n'
                                    "margins/hspace that break the derived box\nRAISE instead of stretching",
             fontsize=8, color=_INK, ha="left", va="bottom", bbox=_BOX, zorder=1001)
    if cell_boxes:
        _outline_cells(fig)
    return fig


def guide_map_facet_anatomy(*, panel_title_h=0.4, cbar_h=0.85, bottom_pad_h=0.15,
                            wspace=0.02, fig_width=12.0, cell_boxes=True):
    """map_facet: title-allowance gaps, bar band, pads — all named, all explicit.

    Parameters are the real map_facet knobs; a changed call re-annotates itself.
    """
    from idd_figures.lib.colors import binned_colormap
    from idd_figures.lib.geo_fixture import SYNTHETIC_EXTENT, make_synthetic_continents
    from idd_figures.lib.layouts.maps import map_facet
    gdf = make_synthetic_continents()
    cmap, norm, _ = binned_colormap([0, 25, 50, 75, 100], base_cmap="RdYlBu_r")
    p = {"gdf": gdf, "value_col": "value", "cmap": cmap, "norm": norm}
    fig = map_facet([
        {"panels": [dict(p, title="A", base_admin_gdf=gdf), dict(p, title="B", base_admin_gdf=gdf),
                    dict(p, title="C", base_admin_gdf=gdf)],
         "extent": SYNTHETIC_EXTENT, "cbar": "shared", "cbar_label": "cbar_label"},
        {"panels": [dict(p, title="D", base_admin_gdf=gdf)], "extent": SYNTHETIC_EXTENT, "cbar": None},
    ], fig_width=fig_width, panel_title_h=panel_title_h, cbar_h=cbar_h,
        bottom_pad_h=bottom_pad_h, wspace=wspace, preview=True)

    m0, m1, m2 = _pos(fig, "map:r0c0"), _pos(fig, "map:r0c1"), _pos(fig, "map:r1c0")
    bar = _pos(fig, "cbar:r0")
    xa = m0.x0 + 0.05  # off the panel titles, which sit at each panel's centre
    _arrow(fig, (xa, m0.y1), (xa, 1.0), f'panel_title_h = {panel_title_h}" (top pad)', dx=0.27, fontsize=8)
    _arrow(fig, (xa, bar.y1), (xa, m0.y0), f'gap = panel_title_h = {panel_title_h}"', dx=0.12, fontsize=8)
    _arrow(fig, (xa, m2.y1), (xa, bar.y0), f'gap = panel_title_h = {panel_title_h}"', dx=0.12, fontsize=8)
    _arrow(fig, (0.988, bar.y0), (0.988, bar.y1), f'cbar_h = {cbar_h}"', rotation=90,
           dx=-0.012, fontsize=7)
    _arrow(fig, (0.85, 0.0), (0.85, m2.y0), f'bottom_pad_h = {bottom_pad_h}"', dy=0.028, fontsize=7)
    _arrow(fig, (m0.x1, (m0.y0 + m0.y1) / 2), (m1.x0, (m0.y0 + m0.y1) / 2),
           f"wspace = {wspace}", dy=0.04, fontsize=8)
    fig.text(m2.x0 + 0.012, (m2.y0 + m2.y1) / 2,
             "row heights are DERIVED:\nmap_row_height(fig_width, margins, ncols, aspect, wspace)\n\n"
             "every inter-row gap IS panel_title_h — titles never survive\non accidental slack; "
             "bars are grid cells spanning the panels they serve",
             fontsize=8, color=_INK, ha="left", va="center", bbox=_BOX, zorder=1001)
    if cell_boxes:
        _outline_cells(fig)
    return fig


def guide_bar_cell_anatomy(*, margin=0.06, spacing=0.03, bin_bottom=0.50,
                           bin_top=0.90, label_gap=0.10, cell_boxes=True):
    """Inside a legend/colorbar cell: the inset knobs, measured from the drawn artists.

    Parameters are the real bin_legend_panel knobs; a changed call re-annotates.
    """
    from idd_figures.lib.colors import binned_colormap
    from idd_figures.lib.painters.legend import bin_legend_panel

    kn = {"margin": margin, "spacing": spacing, "bin_bottom": bin_bottom,
          "bin_top": bin_top, "label_gap": label_gap}
    cmap, norm, colors = binned_colormap([0, 25, 50, 75, 100], base_cmap="RdYlBu_r")
    labels = ["0-25", "25-50", "50-75", "75-100"]

    def discrete(ax, _d=None):
        return bin_legend_panel(ax, colors=colors, labels=labels, **kn)

    def continuous(ax, _d=None):
        import matplotlib.cm as cm
        from matplotlib.colors import Normalize

        sm = cm.ScalarMappable(norm=Normalize(0, 100), cmap="RdYlBu_r")
        sm.set_array([])
        return bin_legend_panel(ax, mappable=sm, use_colorbar=True, cbar_label="cbar_label",
                                margin=kn["margin"], bin_bottom=kn["bin_bottom"],
                                bin_top=kn["bin_top"])

    spec = grid((1, 2), [
        cell((0, 0), paint(discrete, None), name="disc", title="discrete (house default)"),
        cell((0, 1), paint(continuous, None), name="cont", title="continuous"),
    ], margins={"left": 0.03, "right": 0.985, "top": 0.86, "bottom": 0.22}, wspace=0.08)
    fig = panel_grid(spec, figsize=(10, 3.2))

    axd = fig.axes_by_name["disc"]
    pd_ = axd.get_position(original=True)

    def fx(u):  # cell-x fraction -> figure x
        return pd_.x0 + u * pd_.width

    def fy(v):
        return pd_.y0 + v * pd_.height

    r0, r1 = axd.patches[0], axd.patches[1]  # measured swatches, not re-derived
    _arrow(fig, (fx(0.0), fy(0.25)), (fx(r0.get_x()), fy(0.25)),
           f"margin = {kn['margin']}", dy=-0.07, fontsize=8)
    _arrow(fig, (fx(r0.get_x() + r0.get_width()), fy(0.7)), (fx(r1.get_x()), fy(0.7)),
           f"spacing = {kn['spacing']}", dy=0.08, fontsize=8)
    _arrow(fig, (fx(1.02) - 0.005, fy(kn["bin_bottom"])), (fx(1.02) - 0.005, fy(kn["bin_top"])),
           f"bin_bottom = {kn['bin_bottom']} .. bin_top = {kn['bin_top']}",
           rotation=90, dx=0.012, fontsize=8)
    _arrow(fig, (fx(r0.get_x() + r0.get_width() / 2), fy(kn["bin_bottom"])),
           (fx(r0.get_x() + r0.get_width() / 2), fy(kn["bin_bottom"] - kn["label_gap"])),
           f"label_gap = {kn['label_gap']}", dx=0.10, fontsize=8)
    _note(fig, 0.03, "All fractions are OF THE CELL: the cell's grid span is the footprint; these "
                     "knobs set the drawn fill within it. A bar's ink (ticks, cbar_label) must stay "
                     "inside its own cell.", fontsize=8)
    if cell_boxes:
        _outline_cells(fig)
    return fig


def guide_text_placement(*, margins=None, notes=True, cell_boxes=True):
    """Which text hangs OUTSIDE its axes box, and which band must budget it.

    Pass tighter ``margins`` (and ``notes=False`` to clear the caption area) to
    SEE the failure: the tick/label regions crowd the dotted figure boundary —
    the band was the only thing keeping that ink inside the canvas.
    """
    from idd_figures.lib import example_data as ed
    from idd_figures.lib.layouts.anatomy import show_anatomy
    from idd_figures.lib.painters.lines import lines_panel

    margins = {"left": 0.14, "right": 0.95, "top": 0.86, "bottom": 0.30} if margins is None else margins
    df = ed.make_timeseries_df(n_series=2)

    def painter(ax, d):
        lines_panel(ax, d, x="year_id", value="value", hue="series",
                    xlabel="xlabel (hangs below ticks)", ylabel="ylabel (hangs left)")
        return ax

    spec = grid((1, 1), [cell((0, 0), paint(painter, df), name="p", title="title (hangs above)")],
                margins=margins)
    fig = panel_grid(spec, figsize=(8, 5))
    show_anatomy(fig)  # labels panel / title / tick / label regions in colour
    fig.text(0.02, 0.985, f'margins = {margins}', fontsize=8, color=_INK, ha="left",
             va="top", bbox=_BOX, zorder=1001)
    # measured margin bands: margins place the BOX; the hanging text rides along.
    p = fig.axes_by_name["p"].get_position(original=True)
    _arrow(fig, (0.28, p.y1), (0.28, 1.0), f'margins["top"] = {margins["top"]}', dx=0.155, fontsize=8)
    _arrow(fig, (0.80, 0.0), (0.80, p.y0), f'margins["bottom"] = {margins["bottom"]}', dx=0.0,
           dy=0.0, fontsize=8)
    _arrow(fig, (0.0, 0.30), (p.x0, 0.30), f'margins["left"] = {margins["left"]}', dx=0.10,
           dy=0.03, fontsize=8)
    _arrow(fig, (p.x1, 0.30), (1.0, 0.30), f'margins["right"] = {margins["right"]}', dx=-0.09,
           dy=0.03, fontsize=8)
    if notes:
        _note(fig, 0.125, "The grid solver places BOXES (grey panel region). Titles, tick labels and\n"
                          "axis labels render OUTSIDE the box — every one needs an explicit band:",
              fontsize=8)
        _note(fig, 0.068, "above: panel_title_h (map_facet) / title_h (map_panel);  below: bar cells\n"
                          "contain their text; a PLAIN axes bottom row needs bottom_pad ~= 0.5\", not 0.15\".",
              fontsize=8)
        _note(fig, 0.01, "Text extents exist only after a draw -> the coming assert_no_clipping(fig)\n"
                         "guard is post-draw by necessity.", fontsize=8)
    if cell_boxes:
        _outline_cells(fig)
    return fig


def guide_text_styles(*, suptitle_size=13, title_size=20, title_weight="bold",
                      xlabel_size=16, ylabel_size=11, xtick_size=8, ytick_size=13,
                      cell_boxes=True):
    """Every text 'thing' styled INDEPENDENTLY, labelled with the exact call that owns it.

    matplotlib has no single per-region "font" knob: each text object belongs to
    a setter (``set_title``/``set_xlabel``/``tick_params``/...), and WHOLESALE
    changes go through ``mpl.rc_context({...})`` around figure creation. Sizes
    here are deliberately mismatched so each owner is visible; change any
    parameter and its label updates (the changed-version mechanism).
    """
    from idd_figures.lib import example_data as ed
    from idd_figures.lib.painters.lines import lines_panel

    df = ed.make_timeseries_df(n_series=2)

    def painter(ax, d):
        return lines_panel(ax, d, x="year_id", value="value", hue="series")

    spec = grid((1, 1), [cell((0, 0), paint(painter, df), name="p")],
                margins={"left": 0.10, "right": 0.60, "top": 0.84, "bottom": 0.16})
    fig = panel_grid(spec, figsize=(11, 5.5))
    ax = fig.axes_by_name["p"]

    fig.suptitle("suptitle", fontsize=suptitle_size, x=0.35, y=0.97)
    ax.set_title("title", fontsize=title_size, fontweight=title_weight)
    ax.set_xlabel("xlabel", fontsize=xlabel_size)
    ax.set_ylabel("ylabel", fontsize=ylabel_size, fontstyle="italic")
    ax.tick_params(axis="x", labelsize=xtick_size)
    ax.tick_params(axis="y", labelsize=ytick_size)
    for t in ax.get_yticklabels():
        t.set_fontweight("bold")

    calls = [
        f'fig.suptitle(..., fontsize={suptitle_size})',
        f'ax.set_title(..., fontsize={title_size}, fontweight="{title_weight}")',
        f'ax.set_xlabel(..., fontsize={xlabel_size})',
        f'ax.set_ylabel(..., fontsize={ylabel_size}, fontstyle="italic")',
        f'ax.tick_params(axis="x", labelsize={xtick_size})',
        f'ax.tick_params(axis="y", labelsize={ytick_size})',
        'for t in ax.get_yticklabels(): t.set_fontweight("bold")',
    ]
    for i, s in enumerate(calls):
        fig.text(0.63, 0.88 - i * 0.105, s, fontsize=8, color=_INK, ha="left", va="top",
                 bbox=_BOX, zorder=1001)
    _note(fig, 0.015, "No single per-region 'font' knob: every text object has an owner-setter.\n"
                      "Wholesale defaults (family, base size) go through mpl.rc_context({...}) "
                      "around figure creation.", fontsize=8)
    if cell_boxes:
        _outline_cells(fig)
    return fig


def guide_coordinate_frames(*, letter_xy=(0.04, 0.92), cell_boxes=True):
    """The SAME letter placed via axes coords vs figure coords — then the layout changes.

    Top row: both letters coincide visually. Bottom row (taller panels): the
    transAxes letter travels with its panel; the transFigure letter stays glued
    to the canvas point captured in the top row — now visibly wrong. Moral:
    pick the frame that owns the thing you're anchoring to. ``letter_xy`` is the
    axes-fraction address; change it and both placements (and their printed
    coordinates) follow.
    """
    lx, ly = letter_xy
    spec = grid((2, 2), [
        cell((0, 0), paint(_empty, None), name="ax_frame_0", title='ax.text(..., transform=ax.transAxes)'),
        cell((0, 1), paint(_empty, None), name="fig_frame_0", title="fig.text(x, y)  [figure coords]"),
        cell((1, 0), paint(_empty, None), name="ax_frame_1"),
        cell((1, 1), paint(_empty, None), name="fig_frame_1"),
    ], height_ratios=[1, 2], margins={"left": 0.06, "right": 0.97, "top": 0.90, "bottom": 0.16},
        wspace=0.15, hspace=0.55)
    fig = panel_grid(spec, figsize=(9, 6))

    # SAME address in axes coords, used in both rows -> the letter tracks its panel
    for nm in ("ax_frame_0", "ax_frame_1"):
        ax = fig.axes_by_name[nm]
        ax.text(lx, ly, "A", transform=ax.transAxes, va="top", ha="left",
                fontsize=18, fontweight="bold", color=_INK)
        ax.text(lx + 0.10, ly - 0.02, f"({lx}, {ly}) in transAxes", transform=ax.transAxes,
                va="top", fontsize=8, color=_INK)

    # figure-coord address CAPTURED once from the TOP-right panel's corner and
    # drawn once on the canvas: it coincides with that panel — and with nothing else
    p0 = _pos(fig, "fig_frame_0")
    fx, fy = p0.x0 + lx * p0.width, p0.y0 + ly * p0.height
    fig.text(fx, fy, "A", va="top", ha="left", fontsize=18, fontweight="bold", color=_INK)
    fig.text(fx + 0.035, fy - 0.004, f"({fx:.3f}, {fy:.3f}) in figure coords", va="top",
             fontsize=8, color=_INK)
    # the bottom-right panel reuses that SAME address -> no letter appears at its
    # corner, because the canvas point did not move when the panel did
    p1 = _pos(fig, "fig_frame_1")
    corner = (p1.x0 + lx * p1.width, p1.y0 + ly * p1.height)
    fig.add_artist(FancyArrowPatch(corner, (fx + 0.005, fy - 0.02), arrowstyle="->",
                                   mutation_scale=10, color="0.4", lw=1.0, linestyle=":",
                                   transform=fig.transFigure))
    fig.text(min(corner[0] + 0.015, 0.62), corner[1] - 0.012,
             "the figure-coord letter stayed at its canvas\npoint ↑ (did not follow this panel)",
             fontsize=8, color="0.35", va="top")
    _note(fig, 0.055, "One physical point, many addresses: transData glues to the data;\n"
                      "transAxes (0-1 of the panel) glues to the panel; figure coords glue to the canvas.",
          fontsize=8)
    _note(fig, 0.008, "All frames interconvert exactly (ax.transAxes.transform ->\n"
                      "fig.transFigure.inverted().transform) — anything can be forced anywhere, explicitly.",
          fontsize=8)
    if cell_boxes:
        _outline_cells(fig)
    return fig
