import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from shiny import App, render, ui

# Load world boundaries and states (using Natural Earth via GeoPandas)
world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
# For demonstration, use US states from Natural Earth (can be extended for other countries)
try:
    states = gpd.read_file(gpd.datasets.get_path("naturalearth_us_states"))
except Exception:
    states = gpd.GeoDataFrame()  # fallback if not available

country_options = {name: name for name in sorted(world["name"].unique())}

app_ui = ui.page_fluid(
    ui.row(
        ui.column(
            4,
            ui.input_select("country", "Select Country", country_options, selected="United States"),
        ),
        ui.column(
            8,
            ui.output_plot("country_map"),
        ),
    )
)


def plot_country_and_states(country_name):
    fig, ax = plt.subplots(figsize=(8, 6))
    country = world[world["name"] == country_name]
    if not country.empty:
        country.boundary.plot(ax=ax, color="black", linewidth=2)
        # Plot states if available and country is US
        if country_name == "United States" and not states.empty:
            states.boundary.plot(ax=ax, color="blue", linewidth=1)
        ax.set_title(f"{country_name} and its States", fontsize=16)
        ax.set_axis_off()
    else:
        ax.text(0.5, 0.5, f"No data for {country_name}", ha="center", va="center", fontsize=14)
        ax.set_axis_off()
    plt.tight_layout()
    return fig


def server(input, output, session):
    @output()
    @render.plot
    def country_map():
        country_name = input.country()
        return plot_country_and_states(country_name)


app = App(app_ui, server)

if __name__ == "__main__":
    app.run()


# Utility function for raster plot data
def get_raster_plot_data(plot_dict):
    np.random.seed(42)
    raster_data = np.random.rand(10, 10) * plot_dict["bin_n"]
    bins = np.linspace(0, plot_dict["bin_n"], plot_dict["bin_n"] + 1)
    bin_labels = [str(int(b)) for b in bins[:-1]]
    cmap = plt.get_cmap(plot_dict["cmap_name"])
    norm = plt.Normalize(vmin=0, vmax=plot_dict["bin_n"])
    plot_dict["raster_data"] = raster_data
    plot_dict["bins"] = bins
    plot_dict["bin_labels"] = bin_labels
    plot_dict["cmap"] = cmap
    plot_dict["norm"] = norm
    plot_dict["colorbar_label"] = plot_dict.get("colorbar_label", "Fake Value")
    plot_dict["colorbar_title_font_size"] = plot_dict.get("colorbar_title_font_size", 10)
    plot_dict["shrink"] = plot_dict.get("shrink", 0.8)
    plot_dict["pad"] = plot_dict.get("pad", 0.1)
    plot_dict["aspect"] = plot_dict.get("aspect", 30)
    plot_dict["fraction"] = plot_dict.get("fraction", 0.05)
    return plot_dict

    @output()
    @render.plot
    def raster_plot():
        plot_dict = {
            "bin_n": input.bin_n_r(),
            "cmap_name": input.cmap_name_r(),
            "tick_font_size": 8,
            "colorbar_label": "Fake Value",
            "colorbar_title_font_size": 10,
            "shrink": 0.8,
            "pad": 0.1,
            "aspect": 30,
            "fraction": 0.05,
            "use_colorbar": input.use_colorbar_r(),
            "fig_width": input.fig_width_r(),
            "fig_height": input.fig_height_r(),
            "linewidth": input.linewidth_r(),
            "title": "Fake Raster Map",
            "statistic": "mean",
            "map_type": "change",
            "per_capita": False,
            "data_type": "raster",
            "location_type": "endemic",
            "have_legend_panel": True,
            "base_path": None,
            "save_figure": True,
            "remake_figure": False,
            "return_figure": False,
        }
        plot_dict = get_raster_plot_data(plot_dict)
        fig, ax = plt.subplots(figsize=(plot_dict["fig_width"], plot_dict["fig_height"]))
        ax.set_position([0.1, 0.2, 0.8, 0.7])
        im = ax.imshow(
            plot_dict["raster_data"], cmap=plot_dict["cmap"], norm=plot_dict["norm"], origin="lower"
        )
        if plot_dict["use_colorbar"]:
            cbar = fig.colorbar(
                im,
                ax=ax,
                orientation="horizontal",
                shrink=plot_dict["shrink"],
                pad=plot_dict["pad"],
                aspect=plot_dict["aspect"],
                fraction=plot_dict["fraction"],
            )
            cbar.set_ticklabels(plot_dict["bin_labels"])
            cbar.set_label(
                plot_dict["colorbar_label"], fontsize=plot_dict["colorbar_title_font_size"]
            )
        ax.set_title(plot_dict["title"], fontsize=16)
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout()
        return fig


app = App(app_ui, server)

if __name__ == "__main__":
    app.run()
