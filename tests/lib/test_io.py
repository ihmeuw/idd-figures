"""Unit tests for idd_figures.lib.io.

Writes go to a repo-local scratch dir (never /tmp) that is removed after each test.
"""

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from idd_figures.lib.io import save_figure


@pytest.fixture
def out_dir():
    d = Path(__file__).resolve().parent / "_io_out"
    d.mkdir(exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_writes_requested_formats(out_dir):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    written = save_figure(fig, out_dir / "f", formats=["png", "pdf"])
    plt.close(fig)
    assert [Path(p).suffix for p in written] == [".png", ".pdf"]
    assert all(Path(p).exists() for p in written)


def test_preview_figures_get_suffixed_and_cannot_overwrite_finals(out_dir):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    fig._idd_preview = True  # what map_panel(draw_data=False) / map_facet(preview=True) set
    written = save_figure(fig, out_dir / "f", formats=["png"])
    plt.close(fig)
    assert Path(written[0]).name == "f_preview.png"


def test_pdf_fonttype_scoped_not_leaked(out_dir):
    # the PDF save must not mutate global rcParams (rc_context-scoped fonttype)
    import matplotlib as mpl

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    before = mpl.rcParams["pdf.fonttype"]
    save_figure(fig, out_dir / "h", formats=["pdf"])
    plt.close(fig)
    assert mpl.rcParams["pdf.fonttype"] == before


def test_never_uses_tight_bbox(out_dir, monkeypatch):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    seen = {}
    monkeypatch.setattr(fig, "savefig", lambda out, **kw: seen.update(kw))
    save_figure(fig, out_dir / "g", formats=["png"])
    plt.close(fig)
    assert seen["bbox_inches"] is None
    assert seen["pad_inches"] == 0.0
