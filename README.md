# IDD Figures

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-managed-blue.svg)](https://docs.astral.sh/uv/)

Shared, publication-quality figure library for IDD work: painters (lines, scatter,
trajectories, bars, composition, maps, legends), a GridSpec layout engine, and
plotting primitives (bins, colors, palettes, numbers, style, frames, io).

## Installation

### Cluster / development (conda interpreter + uv)

conda provides only the Python interpreter; uv installs and manages every Python
dependency from `pyproject.toml` / `uv.lock`:

```bash
conda env create -f environment.yml    # interpreter-only env
conda activate idd-figures
python -m pip install uv               # per-env uv, same idiom as pip install poetry
UV_PROJECT_ENVIRONMENT=$CONDA_PREFIX uv sync --all-extras
```

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
