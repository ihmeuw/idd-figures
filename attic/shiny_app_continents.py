import matplotlib.pyplot as plt
from shiny import App, render, ui

# Define continents and their bounding boxes (approximate)
continents = {
    "Africa": [-20, 55, -35, 40],
    "Asia": [25, 180, -10, 80],
    "Europe": [-25, 45, 35, 72],
    "North America": [-170, -30, 5, 85],
    "South America": [-90, -30, -60, 15],
    "Oceania": [110, 180, -50, 10],
}
continent_options = {c: c for c in continents}

app_ui = ui.page_fluid(
    ui.row(
        ui.column(
            4,
            ui.input_select("continent", "Select Continent", continent_options, selected="Africa"),
        ),
        ui.column(
            8,
            ui.output_plot("continent_map"),
        ),
    )
)

import numpy as np
from matplotlib import cm


def plot_countries_in_continent_cartopy(continent_name):
    import cartopy.io.shapereader as shpreader
    from shapely.geometry import box
    from shapely.ops import split

    fig = plt.figure(figsize=(10, 7))
    ax = plt.axes()
    bounds = continents[continent_name]
    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])
    ax.set_facecolor("#A6B6DC")  # ocean color

    # Get country polygons for the continent
    reader = shpreader.natural_earth(
        resolution="110m", category="cultural", name="admin_0_countries"
    )
    records = [rec for rec in reader.records() if rec.attributes.get("CONTINENT") == continent_name]
    np.random.seed(42)
    country_values = np.random.rand(len(records)) * 100 if records else []
    vmin, vmax = (country_values.min(), country_values.max()) if len(country_values) else (0, 1)
    bins = np.linspace(vmin, vmax, 6)
    cmap = cm.get_cmap("viridis", len(bins) - 1)

    def recursive_split(poly, depth=0, max_depth=10):
        # Recursively split bounding box of poly
        if depth >= max_depth:
            return [poly]
        minx, miny, maxx, maxy = poly.bounds
        if depth % 2 == 0:
            # vertical split
            x_split = np.random.uniform(minx + 0.2 * (maxx - minx), maxx - 0.2 * (maxx - minx))
            splitter = box(x_split, miny, x_split, maxy)
        else:
            # horizontal split
            y_split = np.random.uniform(miny + 0.2 * (maxy - miny), maxy - 0.2 * (maxy - miny))
            splitter = box(minx, y_split, maxx, y_split)
        try:
            parts = split(poly, splitter)
            result = []
            for part in parts:
                result.extend(recursive_split(part, depth + 1, max_depth))
            return result
        except Exception:
            return [poly]

    for idx, (rec, val) in enumerate(zip(records, country_values)):
        geom = rec.geometry
        bin_idx = np.digitize(val, bins) - 1
        color = cmap(bin_idx / (len(bins) - 2))
        # Draw country polygon
        ax.add_patch(
            plt.Polygon(
                list(geom.exterior.coords),
                facecolor=color,
                edgecolor="black",
                linewidth=2,
                zorder=2,
            )
        )
        # Partition country into contiguous fake states
        admin1s = recursive_split(geom, depth=0, max_depth=4)
        for admin1 in admin1s:
            if admin1.area < 0.01:
                continue
            state_val = np.random.rand() * 100
            state_bin_idx = np.digitize(state_val, bins) - 1
            state_color = cmap(state_bin_idx / (len(bins) - 2))
            try:
                ax.add_patch(
                    plt.Polygon(
                        list(admin1.exterior.coords),
                        facecolor=state_color,
                        edgecolor="white",
                        linewidth=1,
                        zorder=3,
                    )
                )
            except Exception:
                continue
        # Label country
        centroid = geom.centroid
        ax.text(
            centroid.x,
            centroid.y,
            rec.attributes.get("NAME", f"Country {idx + 1}"),
            ha="center",
            va="center",
            fontsize=10,
            color="black",
            zorder=4,
        )

    # Add colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation="horizontal", pad=0.05, aspect=40)
    cbar.set_label("Random Value", fontsize=12)

    ax.set_title(f"Countries and Fake States in {continent_name}", fontsize=16)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.tight_layout()
    return fig


def server(input, output, session):
    @output()
    @render.plot
    def continent_map():
        continent_name = input.continent()
        return plot_countries_in_continent_cartopy(continent_name)


app = App(app_ui, server)

if __name__ == "__main__":
    app.run()
