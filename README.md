# IDD Models and Data

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ihmeuw/idd-models-and-data/HEAD)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![R](https://img.shields.io/badge/r-4.3-blue.svg)](https://www.r-project.org/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blue.svg)](https://python-poetry.org/)

Repository for IDD models and data analysis, supporting both Python and R workflows.

## 🚀 Quick Start

### Launch Interactive Apps
**👆 Click the Binder badge above, then open [`app_launcher.ipynb`](app_launcher.ipynb)**

This repository includes interactive Shiny applications for epidemiological modeling:

- **📊 Multi-Tab Dashboard** - Complete dashboard with multiple analysis tabs
- **🔬 SIR Model Demo** - Interactive demonstration of SIR epidemiological model  
- **⚖️ Model Comparison** - Compare SIR, SEIR, and SEIRS models side by side

### How to Use:
1. **Click the Binder badge** to launch the environment
2. **Open `app_launcher.ipynb`** in the file browser
3. **Run the cells** to see available apps
4. **Select and launch** any app with a single click
5. **Access via `/proxy/8000/`** (replace `/lab` in your browser URL)

## Quick Start with Binder

Click the Binder badge above to launch an interactive environment in your browser with all dependencies pre-installed.

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