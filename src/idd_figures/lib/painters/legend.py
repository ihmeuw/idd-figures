"""Discrete bin legend (and colorbar) painter — GENERAL, not map-specific.

A binned colour ramp rendered as its OWN panel: rectangle swatches + labels (the
default), or a continuous colorbar. Any figure that bins values (maps, heatmaps,
choropleths) can drop this into a reserved layout cell. No geo dependency.
"""

from __future__ import annotations

import numpy as np
from matplotlib.patches import Rectangle

__all__ = ["bin_legend_panel"]


def bin_legend_panel(
    ax,
    *,
    colors=None,
    labels=None,
    mappable=None,
    use_colorbar=False,
    orientation="horizontal",
    edgecolor="black",
    edge_lw=0.5,
    fontsize=10,
    spacing=0.01,
    margin=0.05,
    bin_bottom=0.45,
    bin_top=0.85,
    label_gap=0.08,
):
    """Draw a discrete bin legend (default) or a colorbar onto ``ax``; return ``ax``.

    Discrete (``use_colorbar=False``): centred rectangle swatches from ``colors`` with
    ``labels`` beneath — ports the map ``draw_legend_bins`` behaviour, generalised.
    Colorbar (``use_colorbar=True``): ``fig.colorbar(mappable, cax=ax, ...)``.
    """
    ax.axis("off")
    if use_colorbar:
        if mappable is None:
            msg = "use_colorbar=True requires mappable="
            raise ValueError(msg)
        # Fill EXACTLY the rectangle the discrete swatches would occupy — margin..1-margin
        # wide, bin_bottom..bin_top tall — via an inset, so a continuous ramp matches the
        # binned legend by default (same knobs alter both). The colorbar lives on the inset,
        # not the axis-off cell, so its numeric ticks render.
        cax = ax.inset_axes([margin, bin_bottom, 1 - 2 * margin, bin_top - bin_bottom])
        cbar = ax.figure.colorbar(mappable, cax=cax, orientation=orientation)
        cbar.outline.set_linewidth(edge_lw)
        if labels is not None:
            cbar.set_ticklabels(labels, fontsize=fontsize)
        else:
            cbar.ax.tick_params(labelsize=fontsize)  # keep auto numeric ticks, just size them
        return ax

    if colors is None:
        msg = "discrete legend requires colors="
        raise ValueError(msg)
    n = len(colors)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    width = (1 - 2 * margin - (n - 1) * spacing) / n
    lefts = margin + np.arange(n) * (width + spacing)
    lefts = lefts + (0.5 - (lefts + width / 2).mean())  # centre the row of swatches
    height = bin_top - bin_bottom
    for i in range(n):
        ax.add_patch(
            Rectangle((lefts[i], bin_bottom), width, height, facecolor=colors[i],
                      edgecolor=edgecolor, linewidth=edge_lw)
        )
        if labels is not None:
            ax.text(lefts[i] + width / 2, bin_bottom - label_gap, labels[i],
                    ha="center", va="top", fontsize=fontsize)
    return ax
