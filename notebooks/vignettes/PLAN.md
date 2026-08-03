# Vignette curriculum — roadmap

Bobby's spec (2026-08-02): "there is actually a lot needed to walk through."
Every vignette is import-only (STANDARDS §Notebooks): it imports library
functions — including the `lib/guides.py` anatomy figures — and never defines
a `def`. Each one includes a minimal example of the REQUIRED INPUT DATA and
any extra files (shapefiles etc.), using built-in fixtures wherever possible
(`geo_fixture.make_synthetic_continents`, `example_data.*`).

## Status key
(built) = guide figure exists in lib/guides.py · (parked) = awaiting spec/example

## 1. Tour: the kinds of figures
What the library can make — one exemplar per figure family (lines, scatter,
bars, maps, composition, mixed composites), each with its input-data shape
shown as a tiny tidy DataFrame. Draws on lib/examples.py exemplars.

## 2. Layout anatomy (built — 6 guide figures)
grid_anatomy, map_panel_anatomy, map_facet_anatomy, bar_cell_anatomy,
text_placement, coordinate_frames. The "which number controls which space"
walk-through, R-par()-diagram style, all values live.

## 3. Text: everything you can set
Titles / subtitles / suptitles / panel letters / axis labels / tick labels /
legend text / cbar labels: which function owns each, which band budgets it,
fonts and sizes (rc_context), width-relative sizing policy (their §7.6 ask,
Bobby-endorsed). Includes the plotting-options section (nested-margins
alternative — "the parent's cell IS the margin control"). (parked: Bobby has
specific ideas — collect before writing.)

## 4. PDF-editable text
Why fonttype 42, what Illustrator sees, what journals reject; save_figure's
rc_context scoping; multi-format saves, DPI defaults, thumbnails, the
_preview suffix interlock.

## 5. Maps, the whole surface
ocean/lakes/coastlines/borders toggles (Natural Earth: network on first use —
and the coastline-mismatch caution vs our admin shapefiles; Bobby has a
workaround example to fold in), raster vs choropleth, adding points, disputed
boundaries, projections (PlateCarree default; what changes under others —
projected-unit aspect), simplified-vs-full shapefile discipline, preview
mode, map_facet. Input files section: what a shapefile/GeoDataFrame must
contain (join key, geometry, CRS).

## 6. Color choices (Bobby ask, 2026-08-02: "if we are doing color bars, do we
have a vignette on color choices?")
The palette law (red is bad, always; blue never bad; yellow mid-ramp only —
lsae's three-rounds-in-a-day lesson), binned-first house default vs continuous,
sequential vs diverging vs split-middle (`remove_middle` symmetric spec,
`clipped_diverging_cmap` when built), pin-and-saturate vs full-data-range
limits, the house palettes (`GBD_SUPER_REGION_COLORS` after the lsae hex
adoption, greys/median markers), colour-blindness constraints. Guide figure:
`binned_colormap` anatomy (drop_light / force_white_zero / remove_middle /
diverging) in the changed-version style.

## 7. One vignette per plot family
lines/timeseries · scatter · range bars · composition (ternary) · heatmap
(when built). Each: input-data contract, painter knobs, common pitfalls,
"control all the things" worked example (Bobby's phrase — collect his spec).

## Backlog feeding these
- assert_no_clipping(fig) post-draw guard (companion to the aspect guard).
- Palette adoption + clipped_diverging_cmap + numbers.compact (prep 16-18).
- Ocean-coastline workaround example (Bobby to supply).
