# IDD Figures

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blue.svg)](https://python-poetry.org/)

Repository for IDD figures and interactive plotting tools in Python.

## 🚀 Quick Start

### Launch Interactive Shiny App

You can launch an interactive Python Shiny app to explore map figures with sliders and dropdowns for plot options (e.g., number of bins, colormap):

#### 1. Install dependencies

Make sure your environment includes:
- shiny
- geopandas
- matplotlib
- numpy

If using conda:
```bash
conda install -c conda-forge shiny geopandas matplotlib numpy
```
Or with pip:
```bash
pip install shiny geopandas matplotlib numpy
```

#### 2. Run the app

```bash
python src/idd_figures/shiny_app.py
```

This will start a local Shiny server. Open the provided URL in your browser to interact with the app.

---

## Local Installation

### Option 1: Using Conda (Recommended)

```bash
# Clone the repository
git clone https://github.com/ihmeuw/idd-figures.git
cd idd-figures

# Create and activate the conda environment
conda env create -f environment.yml
conda activate idd-figures
```

### Option 2: Install as a Python package (from GitHub)

You can install and use `idd_figures` in other projects/environments:

```bash
pip install git+https://github.com/ihmeuw/idd-figures.git
```

Then, in your Python code:

```python
from idd_figures import plot_map

def get_plot_data(plot_dict):
    # User-defined logic to prepare plot_dict for plotting
    return plot_dict

plot_map(plot_dict, get_plot_data)
```