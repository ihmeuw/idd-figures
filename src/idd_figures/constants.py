"""Project-wide constants for idd-figures.

Holds default styling values, relative path *fragments*, and enums shared
across modules. Never put absolute filesystem paths here — those live in
``paths.yaml`` (loaded via :mod:`idd_figures.paths`). See STANDARDS §Path safety.
"""

# Default colormap for choropleth / sequential figures.
DEFAULT_CMAP = "Reds"

# Default global map extent: [lon_min, lon_max, lat_min, lat_max].
DEFAULT_MAP_EXTENT = (-180, 180, -90, 90)

# idd_beeswarm solver defaults (mirror the function-signature defaults; keep
# in sync if those change).
DEFAULT_GAP_FRACTION = 0.1
DEFAULT_MARGIN = 0.5
