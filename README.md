# IDD Figures

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-managed-blue.svg)](https://docs.astral.sh/uv/)

Shared, publication-quality figure library for IDD work: painters (lines, scatter,
trajectories, bars, composition, maps, legends), a GridSpec layout engine, and
plotting primitives (bins, colors, palettes, numbers, style, frames, io).

## Installation

### Cluster / development (uv-managed .venv)

uv owns everything: the project `.venv`, its interpreter (a uv-managed CPython —
conda is not involved), and every dependency from `pyproject.toml` / `uv.lock`:

```bash
uv python install 3.12    # one-time per user (deliberate download; policy is python-downloads = "manual")
uv venv --python 3.12     # .venv in the repo root
uv sync --all-extras
.venv/bin/python -m pytest tests/    # verify
```

Run code via `.venv/bin/python` (absolute path in Slurm jobs — no activation
needed). For notebooks: `.venv/bin/python -m ipykernel install --user --name
idd-figures --display-name "idd-figures (.venv)"`.

### As a dependency (pip)

Core installs only numpy/pandas/matplotlib. Heavy dependencies are opt-in extras:
`maps` (cartopy, geopandas, shapely), `ternary` (mpltern), `thumbnails` (pillow),
`config` (pyyaml), or `all`.

```bash
pip install "idd-figures[maps] @ git+https://github.com/ihmeuw/idd-figures.git"
```

## Usage

Consumers use submodule imports; the top-level package imports nothing heavy:

```python
from idd_figures.lib import example_data as ed
from idd_figures.lib.colors import binned_colormap
from idd_figures.lib.painters.maps import basemap_painter, choropleth_painter
```

Painters draw on an existing `Axes` and return it; layouts own the `Figure`/`GridSpec`.
See `notebooks/vignettes/` for worked examples (painters, layouts, maps).

## Tests

```bash
python -m pytest
```
