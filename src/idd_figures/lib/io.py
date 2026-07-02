"""Caller-invoked figure saving. Painters and layouts NEVER save; callers do.

Hard rule: we never use ``bbox_inches="tight"`` — it defeats the explicit
GridSpec placement model (it would crop/re-pad and break cross-figure
alignment). Saves use the figure's exact declared size.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["save_figure"]

_DEFAULT_DPI = {"pdf": 720, "png": 360}


def save_figure(fig, path, *, formats=None, dpi=None, pad_inches=0.0, chmod=None, thumbnail=0.0):
    """Save ``fig`` to ``path`` in one or more formats; return the written paths.

    ``path`` may be given with or without an extension. ``formats`` defaults to
    the path's extension, else ``["pdf"]``. Parent directories are created.
    Always ``bbox_inches=None`` (never "tight"). ``chmod`` (e.g. ``0o775``) is
    applied only if given. ``thumbnail`` in ``(0, 1]`` writes an extra downscaled
    PNG alongside any PNG output (lazy PIL import).
    """
    path = Path(path)
    if formats is None:
        formats = [path.suffix.lstrip(".")] if path.suffix else ["pdf"]
    base = path.with_suffix("")
    base.parent.mkdir(parents=True, exist_ok=True)

    written = []
    for fmt in formats:
        out = base.with_suffix(f".{fmt}")
        d = dpi if dpi is not None else _DEFAULT_DPI.get(fmt, 300)
        if fmt == "pdf":
            import matplotlib as mpl

            mpl.rcParams["pdf.fonttype"] = 42  # editable text in the PDF
        fig.savefig(out, format=fmt, dpi=d, bbox_inches=None, pad_inches=pad_inches)
        if chmod is not None:
            os.chmod(out, chmod)  # noqa: PTH101 -- intentional, mode passed by caller
        written.append(out)
        if thumbnail and thumbnail > 0.0 and fmt == "png":
            written.append(_save_thumbnail(out, thumbnail, d))
    return written


def _save_thumbnail(png_path, fraction, dpi):
    from PIL import Image  # lazy/optional dependency

    img = Image.open(png_path)
    w, h = img.size
    thumb = img.resize((max(int(w * fraction), 1), max(int(h * fraction), 1)), Image.LANCZOS)
    out = png_path.with_name(png_path.stem + "_thumbnail.png")
    thumb.save(out, dpi=(dpi, dpi))
    return out
