# Kept intentionally empty so `import idd_figures` never pulls in optional heavy
# deps (cartopy / geopandas / mpltern). Import explicitly from the lib subpackages:
#   from idd_figures.lib.painters.lines import lines_panel
#   from idd_figures.lib.layouts.grids import panel_grid, facet_grid
#   from idd_figures.lib.bins import map_bin_labels
# (The pre-engine idd_figures.plot_map prototype now lives in attic/, pending the map port.)
