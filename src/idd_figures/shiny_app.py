
import shiny
from shiny import App, ui, render, reactive, Inputs, Outputs
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
from idd_figures import plot_map

# Load sample country shapefile (Natural Earth, low-res)
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

# Fake data generator for demonstration
def get_plot_data(plot_dict):
    world_copy = world.copy()
    np.random.seed(42)
    world_copy['value'] = np.random.rand(len(world_copy)) * plot_dict['bin_n']
    bins = np.linspace(0, plot_dict['bin_n'], plot_dict['bin_n'] + 1)
    bin_labels = [str(int(b)) for b in bins[:-1]]
    bin_colors = plt.get_cmap(plot_dict['cmap_name'])(np.linspace(0, 1, plot_dict['bin_n']))
    cmap = plt.get_cmap(plot_dict['cmap_name'])
    norm = plt.Normalize(vmin=0, vmax=plot_dict['bin_n'])
    plot_dict['map_dict'] = {
        'admin0_polygons': world_copy,
        'admin1_polygons': world_copy,
        'admin2_polygons': world_copy,
        'map_extent': [-180, 180, -90, 90],
        'plot_admin1s': False
    }
    plot_dict['figure_dict'] = {
        'water_color': 'lightblue',
        'water_alpha': 0.5,
        'bin_labels': bin_labels,
        'tick_font_size': plot_dict.get('tick_font_size', 8),
        'colorbar_label': plot_dict.get('colorbar_label', 'Fake Value'),
        'colorbar_title_font_size': plot_dict.get('colorbar_title_font_size', 10)
    }
    plot_dict['legend_dict'] = {
        'color_bar_dict': {
            'shrink': plot_dict.get('shrink', 0.8),
            'pad': plot_dict.get('pad', 0.1),
            'aspect': plot_dict.get('aspect', 30),
            'fraction': plot_dict.get('fraction', 0.05)
        }
    }
    plot_dict['bin_dict'] = {
        'bins': bins,
        'bin_colors': bin_colors,
        'cmap': cmap,
        'norm': norm
    }
    plot_dict['data_dict'] = {
        'plot_data': world_copy,
        'data_column': 'value'
    }
    plot_dict['map_a1_loc_ids'] = None
    plot_dict['map_a2_loc_ids'] = world_copy['name']
    return plot_dict

# Raster data generator for demonstration
def get_raster_plot_data(plot_dict):
    # Create a fake raster (e.g., 180x90 grid for world)
    np.random.seed(42)
    raster_data = np.random.rand(90, 180) * plot_dict['bin_n']
    bins = np.linspace(0, plot_dict['bin_n'], plot_dict['bin_n'] + 1)
    bin_labels = [str(int(b)) for b in bins[:-1]]
    bin_colors = plt.get_cmap(plot_dict['cmap_name'])(np.linspace(0, 1, plot_dict['bin_n']))
    cmap = plt.get_cmap(plot_dict['cmap_name'])
    norm = plt.Normalize(vmin=0, vmax=plot_dict['bin_n'])
    plot_dict['raster_data'] = raster_data
    plot_dict['bins'] = bins
    plot_dict['bin_labels'] = bin_labels
    plot_dict['bin_colors'] = bin_colors
    plot_dict['cmap'] = cmap
    plot_dict['norm'] = norm
    plot_dict['tick_font_size'] = plot_dict.get('tick_font_size', 8)
    plot_dict['colorbar_label'] = plot_dict.get('colorbar_label', 'Fake Value')
    plot_dict['colorbar_title_font_size'] = plot_dict.get('colorbar_title_font_size', 10)
    plot_dict['shrink'] = plot_dict.get('shrink', 0.8)
    plot_dict['pad'] = plot_dict.get('pad', 0.1)
    plot_dict['aspect'] = plot_dict.get('aspect', 30)
    plot_dict['fraction'] = plot_dict.get('fraction', 0.05)
    return plot_dict

# Shiny UI with tabs
app_ui = ui.page_fluid(
    ui.h2("IDD Figures Interactive Demo"),
    ui.navset_tab(
        ui.nav("Polygon Map",
            ui.input_slider("bin_n", "Number of bins", min=3, max=10, value=5),
            ui.input_select("cmap_name", "Colormap", ["Reds", "Blues", "Greens", "viridis", "plasma", "cividis"], selected="Reds"),
            ui.input_slider("tick_font_size", "Tick Font Size", min=6, max=20, value=8),
            ui.input_text("colorbar_label", "Colorbar Label", value="Fake Value"),
            ui.input_slider("colorbar_title_font_size", "Colorbar Title Font Size", min=8, max=24, value=10),
            ui.input_slider("shrink", "Colorbar Shrink", min=0.5, max=1.0, value=0.8, step=0.05),
            ui.input_slider("pad", "Colorbar Pad", min=0.0, max=0.5, value=0.1, step=0.01),
            ui.input_slider("aspect", "Colorbar Aspect", min=10, max=50, value=30),
            ui.input_slider("fraction", "Colorbar Fraction", min=0.01, max=0.2, value=0.05, step=0.01),
            ui.output_plot("map_plot", width="800px", height="500px"),
        ),
        ui.nav("Raster Map",
            ui.input_slider("r_bin_n", "Number of bins", min=3, max=10, value=5),
            ui.input_select("r_cmap_name", "Colormap", ["Reds", "Blues", "Greens", "viridis", "plasma", "cividis"], selected="Reds"),
            ui.input_slider("r_tick_font_size", "Tick Font Size", min=6, max=20, value=8),
            ui.input_text("r_colorbar_label", "Colorbar Label", value="Fake Value"),
            ui.input_slider("r_colorbar_title_font_size", "Colorbar Title Font Size", min=8, max=24, value=10),
            ui.input_slider("r_shrink", "Colorbar Shrink", min=0.5, max=1.0, value=0.8, step=0.05),
            ui.input_slider("r_pad", "Colorbar Pad", min=0.0, max=0.5, value=0.1, step=0.01),
            ui.input_slider("r_aspect", "Colorbar Aspect", min=10, max=50, value=30),
            ui.input_slider("r_fraction", "Colorbar Fraction", min=0.01, max=0.2, value=0.05, step=0.01),
            ui.output_plot("raster_plot", width="800px", height="500px"),
        ),
    )
)

# Shiny server logic
def server(input, output, session):
    @output()
    @render.plot
    def map_plot():
        plot_dict = {
            'bin_n': input.bin_n(),
            'cmap_name': input.cmap_name(),
            'tick_font_size': input.tick_font_size(),
            'colorbar_label': input.colorbar_label(),
            'colorbar_title_font_size': input.colorbar_title_font_size(),
            'shrink': input.shrink(),
            'pad': input.pad(),
            'aspect': input.aspect(),
            'fraction': input.fraction()
        }
        plot_map(plot_dict, get_plot_data)

    @output()
    @render.plot
    def raster_plot():
        plot_dict = {
            'bin_n': input.r_bin_n(),
            'cmap_name': input.r_cmap_name(),
            'tick_font_size': input.r_tick_font_size(),
            'colorbar_label': input.r_colorbar_label(),
            'colorbar_title_font_size': input.r_colorbar_title_font_size(),
            'shrink': input.r_shrink(),
            'pad': input.r_pad(),
            'aspect': input.r_aspect(),
            'fraction': input.r_fraction()
        }
        plot_dict = get_raster_plot_data(plot_dict)
        fig, ax = plt.subplots(figsize=(10, 6))
        im = ax.imshow(plot_dict['raster_data'], cmap=plot_dict['cmap'], norm=plot_dict['norm'], origin='lower')
        cbar = fig.colorbar(im, ax=ax, orientation='horizontal', shrink=plot_dict['shrink'], pad=plot_dict['pad'], aspect=plot_dict['aspect'], fraction=plot_dict['fraction'])
        cbar.set_ticklabels(plot_dict['bin_labels'])
        cbar.set_label(plot_dict['colorbar_label'], fontsize=plot_dict['colorbar_title_font_size'])
        ax.set_title('Fake Raster Map', fontsize=16)
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout()
        return fig

app = App(app_ui, server)
