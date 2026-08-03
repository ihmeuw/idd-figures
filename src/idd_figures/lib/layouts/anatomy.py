"""Figure anatomy overlay: boxes around panels, labels, title, ticks, and margins.

Because we place everything explicitly (never ``tight_layout``), this is the tool
for *seeing exactly where each piece lands*. ``show_anatomy(fig)`` draws labelled,
non-clipping rectangles over: the figure outer bounds, each Axes (panel), and that
Axes' x-label / y-label / title / x-tick / y-tick regions. Diagnostic only — call
it on a finished Figure (it draws the canvas once to measure text).
"""

from __future__ import annotations

import matplotlib.patches as mpatches
from matplotlib.transforms import Bbox

__all__ = ["show_anatomy"]

#: region -> edge colour
REGION_COLORS = {
    "figure": "#888888",
    "panel": "#1f77b4",
    "xlabel": "#2ca02c",
    "ylabel": "#9467bd",
    "title": "#d62728",
    "xticks": "#ff7f0e",
    "yticks": "#8c564b",
}


def _box(fig, x0, y0, w, h, color, *, lw=1.2, ls="-"):
    fig.add_artist(
        mpatches.Rectangle(
            (x0, y0),
            w,
            h,
            transform=fig.transFigure,
            fill=False,
            edgecolor=color,
            lw=lw,
            ls=ls,
            zorder=1000,
            clip_on=False,
        )
    )


def _artist_box(fig, artist, renderer):
    return artist.get_window_extent(renderer=renderer).transformed(fig.transFigure.inverted())


def show_anatomy(fig, *, axes=None, outer=True, key=True):
    """Overlay region boxes on ``fig`` and return it.

    ``axes`` limits which Axes are boxed (default: all). ``outer`` boxes the whole
    figure (so margins show as the gap to each panel). ``key`` adds a small colour
    legend. Box colours are in :data:`REGION_COLORS`.
    """
    fig.canvas.draw()  # need a renderer to measure text extents
    renderer = fig.canvas.get_renderer()

    if outer:
        _box(fig, 0, 0, 1, 1, REGION_COLORS["figure"], lw=1.5, ls=":")

    for ax in axes if axes is not None else fig.axes:
        pos = ax.get_position()
        _box(fig, pos.x0, pos.y0, pos.width, pos.height, REGION_COLORS["panel"])

        for region, artist in (
            ("xlabel", ax.xaxis.label),
            ("ylabel", ax.yaxis.label),
            ("title", ax.title),
        ):
            if artist.get_text():
                bb = _artist_box(fig, artist, renderer)
                _box(fig, bb.x0, bb.y0, bb.width, bb.height, REGION_COLORS[region])

        for region, ticklabels in (
            ("xticks", ax.get_xticklabels()),
            ("yticks", ax.get_yticklabels()),
        ):
            boxes = [t.get_window_extent(renderer) for t in ticklabels if t.get_text()]
            if boxes:
                bb = Bbox.union(boxes).transformed(fig.transFigure.inverted())
                _box(fig, bb.x0, bb.y0, bb.width, bb.height, REGION_COLORS[region], ls="--")

    if key:
        handles = [mpatches.Patch(facecolor=c, label=r) for r, c in REGION_COLORS.items()]
        fig.legend(handles=handles, loc="upper right", fontsize=7, frameon=False, title="anatomy")
    return fig
