# Attic — quarantined, NOT deleted

plot_map.py: pre-engine map prototype (owns Figure, calls plt.show, duplicate get_colors/smart_format/pretty_bin_labels). Superseded by lib/painters/maps.py + lib/bins.py + lib/colors.py + the GridSpec layout engine. Kept to mine any missed nuance; delete once the map port is verified complete (see .claude/memory.md Maps section).
test_plot_map.py: tested the above; now covered by tests/lib/.
shiny_app.py: legacy interactive demo (was src/idd_figures/shiny_app.py). Parked 2026-07-02 during the Poetry→uv migration so the package drags in neither shiny nor the geo stack; also calls gpd.datasets.get_path, removed in geopandas 1.x, so it needs a rewrite before it can run again.
shiny_app_continents.py: older repo-root variant of the same demo (cartopy continent version). Parked same date.
list_apps.py: app launcher copied from idd-models-and-data; imports src.idd_mad.apps, which does not exist in this repo. Parked same date.
