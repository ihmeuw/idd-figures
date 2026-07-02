"""Shared figure library for idd-figures.

Import submodules explicitly (e.g. ``from idd_figures.lib.painters.lines import
lines_panel``). This package deliberately does NOT eagerly import its submodules,
so ``import idd_figures`` and importing any one module never drags in optional
heavy dependencies (mpltern, PIL). Each module imports only what it needs; the
heaviest/optional engines are imported lazily inside the functions that use them.
"""
