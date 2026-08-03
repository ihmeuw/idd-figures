"""GridSpec-based figure layouts: a recursive ``panel_grid`` + ``facet_grid``.

A figure is a tree of GridSpecs. Every position is explicit: we NEVER call
``tight_layout`` / ``constrained_layout``, and saving uses ``bbox_inches=None``
(see :mod:`idd_figures.lib.io`). A cell holds a painter call, a nested grid, or a
reserved slot (label / legend / colorbar / blank). Nesting uses
``GridSpecFromSubplotSpec``.

Build a tree with the small constructors (``grid``, ``cell``, ``paint``,
``label``, ``legend``, ``colorbar``, ``blank``) and realise it with
``panel_grid(spec, figsize=...)``. ``facet_grid`` is sugar that generates the
common faceting trees (small-multiples / row x col) and calls ``panel_grid``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

__all__ = [
    "blank",
    "cell",
    "colorbar",
    "facet_grid",
    "grid",
    "label",
    "legend",
    "paint",
    "panel_grid",
]

# explicit default outer margins (figure fractions) — never tight_layout
_DEFAULT_MARGINS = {"left": 0.08, "right": 0.97, "top": 0.93, "bottom": 0.08}


# --- content nodes -----------------------------------------------------------
@dataclass
class Paint:
    painter: Callable
    data: Any
    kwargs: dict = field(default_factory=dict)


@dataclass
class Label:
    text: str
    kwargs: dict = field(default_factory=dict)


@dataclass
class Legend:
    handles: Any = None  # (handles, labels) tuple
    kwargs: dict = field(default_factory=dict)


@dataclass
class Colorbar:
    mappable: Any
    kwargs: dict = field(default_factory=dict)


@dataclass
class Blank:
    pass


@dataclass
class Cell:
    at: tuple
    content: Any
    name: str | None = None
    projection: Any = None  # stock name (e.g. "polar") or a projection object (e.g. a cartopy CRS)
    sharex: str | None = None
    sharey: str | None = None
    title: str | None = None


@dataclass
class Grid:
    shape: tuple
    cells: list
    height_ratios: list | None = None
    width_ratios: list | None = None
    margins: dict | None = (
        None  # top level only; nested grids raise (the parent's cell IS the margin control)
    )
    wspace: float | None = None
    hspace: float | None = None


# --- constructors (thin, readable call sites) --------------------------------
def grid(shape, cells, **kw):
    return Grid(shape=shape, cells=cells, **kw)


def cell(at, content, **kw):
    return Cell(at=at, content=content, **kw)


def paint(painter, data, **kwargs):
    return Paint(painter, data, kwargs)


def label(text, **kw):
    return Label(text, kw)


def legend(handles=None, **kw):
    return Legend(handles, kw)


def colorbar(mappable, **kw):
    return Colorbar(mappable, kw)


def blank():
    return Blank()


# --- realisation -------------------------------------------------------------
def _as_slice(v):
    return v if isinstance(v, slice) else slice(v, v + 1)


def _make_gs(node, fig, parent_spec):
    if parent_spec is None:
        margins = {**_DEFAULT_MARGINS, **(node.margins or {})}
        return GridSpec(
            *node.shape,
            figure=fig,
            height_ratios=node.height_ratios,
            width_ratios=node.width_ratios,
            wspace=node.wspace,
            hspace=node.hspace,
            **margins,
        )
    if node.margins:
        msg = (
            "nested grids cannot take margins= (matplotlib's nested gridspec has no such "
            "parameter); the parent's cell IS the margin control — shape it, or add spacer "
            "rows/cols"
        )
        raise ValueError(msg)
    return GridSpecFromSubplotSpec(
        *node.shape,
        subplot_spec=parent_spec,
        height_ratios=node.height_ratios,
        width_ratios=node.width_ratios,
        wspace=node.wspace,
        hspace=node.hspace,
    )


def _realize(node, fig, parent_spec, registry):
    gs = _make_gs(node, fig, parent_spec)
    for c in node.cells:
        r, col = c.at
        sub = gs[_as_slice(r), _as_slice(col)]
        content = c.content

        if isinstance(content, Grid):
            _realize(content, fig, sub, registry)
            continue
        if isinstance(content, Blank):
            continue

        share = {}
        if c.sharex:
            share["sharex"] = registry[c.sharex]
        if c.sharey:
            share["sharey"] = registry[c.sharey]
        ax = fig.add_subplot(sub, projection=c.projection, **share)
        if c.name:
            registry[c.name] = ax

        if isinstance(content, Paint):
            content.painter(ax, content.data, **content.kwargs)
        elif isinstance(content, Label):
            kw = dict(content.kwargs)
            ax.axis("off")
            ax.text(
                0.5,
                0.5,
                content.text,
                ha=kw.pop("ha", "center"),
                va=kw.pop("va", "center"),
                transform=ax.transAxes,
                **kw,
            )
        elif isinstance(content, Legend):
            ax.axis("off")
            if isinstance(content.handles, tuple):
                handles, labels = content.handles
                ax.legend(handles, labels, loc="center", **content.kwargs)
        elif isinstance(content, Colorbar):
            fig.colorbar(content.mappable, cax=ax, **content.kwargs)

        if c.title:
            ax.set_title(c.title)


def panel_grid(spec, *, figsize, fig=None):
    """Realise a grid tree ``spec`` into a Figure of the exact ``figsize``.

    No auto-layout is applied. Returns the Figure; the caller owns IO. Named
    cells are retrievable afterwards via ``fig.axes_by_name`` (name -> Axes).
    """
    if fig is None:
        fig = plt.figure(figsize=figsize)
    registry: dict = {}
    _realize(spec, fig, None, registry)
    fig.axes_by_name = registry  # post-layout annotation needs the named cells back
    return fig


def facet_grid(
    data,
    painter,
    *,
    row=None,
    col=None,
    sharex=False,
    sharey=False,
    ncol=None,
    panel_kwargs=None,
    titles=None,
    figsize=(12, 8),
    margins=None,
    wspace=0.25,
    hspace=0.35,
    suptitle=None,
    projection=None,
):
    """Facet ``painter`` over the unique values of ``row`` and/or ``col``.

    With both ``row`` and ``col`` set, builds a ``len(row) x len(col)`` grid; with
    one set, wraps small-multiples into ``ncol`` columns. ``panel_kwargs`` is a
    dict or a callable ``info -> dict`` (where ``info`` is the ``{dim: value}`` for
    that cell); ``titles`` is a callable ``info -> str`` or a mapping. ``sharex`` /
    ``sharey`` link all panels to the first. ``projection`` (stock name or a
    projection object, e.g. a cartopy CRS) is applied to EVERY cell — required for
    facets of maps/ternaries, incompatible with axis sharing. Returns the Figure.
    """
    from idd_figures.lib.frames import panel_slice

    if projection is not None and (sharex or sharey):
        msg = "sharex/sharey are not supported with projection= (projected axes cannot share plain ones)"
        raise ValueError(msg)

    def pk(info):
        if panel_kwargs is None:
            return {}
        return panel_kwargs(info) if callable(panel_kwargs) else dict(panel_kwargs)

    def title_of(info):
        if titles is None:
            return None
        if callable(titles):
            return titles(info)
        return titles.get(tuple(info.values()))

    cells = []
    first = None

    if row and col:
        rvals = sorted(data[row].dropna().unique())
        cvals = sorted(data[col].dropna().unique())
        shape = (len(rvals), len(cvals))
        for i, rv in enumerate(rvals):
            for j, cv in enumerate(cvals):
                info = {row: rv, col: cv}
                name = f"{i}_{j}"
                cells.append(
                    cell(
                        (i, j),
                        paint(painter, panel_slice(data, info), **pk(info)),
                        name=name,
                        projection=projection,
                        sharex=(first if sharex else None),
                        sharey=(first if sharey else None),
                        title=title_of(info),
                    )
                )
                first = first or name
    else:
        facet = row or col
        if facet is None:
            msg = "facet_grid needs at least one of row=/col="
            raise ValueError(msg)
        vals = sorted(data[facet].dropna().unique())
        n = len(vals)
        nc = ncol or min(n, 3)
        nr = -(-n // nc)
        shape = (nr, nc)
        for k, v in enumerate(vals):
            i, j = divmod(k, nc)
            info = {facet: v}
            name = f"{i}_{j}"
            cells.append(
                cell(
                    (i, j),
                    paint(painter, panel_slice(data, info), **pk(info)),
                    name=name,
                    projection=projection,
                    sharex=(first if sharex else None),
                    sharey=(first if sharey else None),
                    title=title_of(info),
                )
            )
            first = first or name

    spec = grid(shape, cells, margins=margins, wspace=wspace, hspace=hspace)
    fig = panel_grid(spec, figsize=figsize)
    if suptitle:
        fig.suptitle(suptitle)
    return fig
