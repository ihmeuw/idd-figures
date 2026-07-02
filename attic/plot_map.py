import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np

# Utility functions


def smart_format(val):
    if float(val).is_integer():
        return f"{int(val)}"
    else:
        s = f"{val:.2f}".rstrip("0").rstrip(".")
        return s


def pretty_bin_labels(bins, le=False, ge=False, zero_bin=False):
    labels = []
    zero_ix = np.where(np.atleast_1d(bins) == 0)[0] if zero_bin else None
    for i in range(len(bins) - 1):
        left = smart_format(bins[i])
        right = smart_format(bins[i + 1])
        if zero_bin and i == zero_ix:
            labels.append("0")
        elif zero_bin and i == zero_ix + 1:
            labels.append(f"0 - {right}")
        elif left == right:
            labels.append(left)
        else:
            labels.append(f"{left}–{right}")
    if le:
        labels[0] = f"< {smart_format(bins[1])}"
    if ge:
        labels[-1] = f"> {smart_format(bins[-2])}"
    return labels


def get_colors(n_bins, cmap_name="Reds"):
    cmap = plt.get_cmap(cmap_name)
    return [cmap(i / (n_bins - 1)) for i in range(n_bins)]


# Plotting functions


def setup_map_plot(ax_map, plot_dict):
    map_dict = plot_dict["map_dict"]
    figure_dict = plot_dict["figure_dict"]
    map_extent = map_dict.get("map_extent", [-180, 180, -90, 90])
    ax_map.set_extent(map_extent, crs=ccrs.PlateCarree())
    ax_map.add_feature(
        cfeature.OCEAN,
        facecolor=figure_dict["water_color"],
        alpha=figure_dict["water_alpha"],
        zorder=0,
    )
    ax_map.coastlines(linewidth=0.5)
    ax_map.add_feature(cfeature.BORDERS, linewidth=0.3, edgecolor="gray")
    return ax_map


def plot_base_admins(ax_map, plot_dict):
    map_dict = plot_dict["map_dict"]
    admin0_polygons = map_dict["admin0_polygons"]
    admin1_polygons = map_dict["admin1_polygons"]
    admin0_polygons.plot(
        ax=ax_map, color="lightgrey", edgecolor="black", linewidth=0, transform=ccrs.PlateCarree()
    )
    if map_dict.get("plot_admin1s", False):
        if plot_dict["map_a1_loc_ids"] is not None:
            admin1s_to_plot = admin1_polygons[
                ~admin1_polygons["location_id"].isin(plot_dict["map_a1_loc_ids"])
            ]
        else:
            admin1s_to_plot = admin1_polygons
        admin1s_to_plot.boundary.plot(
            ax=ax_map, color="darkgrey", linewidth=0.25, transform=ccrs.PlateCarree()
        )


def plot_data_admins(ax_map, plot_dict, linewidth=0):
    data_dict = plot_dict["data_dict"]
    admin2_polygons = plot_dict["map_dict"]["admin2_polygons"]
    admin2_endemic = admin2_polygons[
        admin2_polygons["location_id"].isin(plot_dict["map_a2_loc_ids"])
    ]
    admin2_with_data = admin2_endemic.merge(data_dict["plot_data"], on="location_id", how="left")
    admin2_with_data.plot(
        column=data_dict["data_column"],
        ax=ax_map,
        cmap=plot_dict["bin_dict"]["cmap"],
        norm=plot_dict["bin_dict"]["norm"],
        legend=False,
        edgecolor=None,
        linewidth=linewidth,
        transform=ccrs.PlateCarree(),
    )
    admin0_polygons = plot_dict["map_dict"]["admin0_polygons"]
    admin0_polygons.boundary.plot(
        ax=ax_map, color="black", linewidth=0.5, transform=ccrs.PlateCarree()
    )


def add_colorbar(fig, ax, plot_dict):
    figure_dict = plot_dict["figure_dict"]
    legend_dict = plot_dict["legend_dict"]
    bins = plot_dict["bin_dict"]["bins"]
    bin_centers = [(bins[i] + bins[i + 1]) / 2 for i in range(len(bins) - 1)]
    sm = plt.cm.ScalarMappable(
        cmap=plot_dict["bin_dict"]["cmap"], norm=plot_dict["bin_dict"]["norm"]
    )
    sm.set_array([])
    cbar = fig.colorbar(
        sm,
        ax=ax,
        orientation="horizontal",
        shrink=legend_dict["color_bar_dict"]["shrink"],
        pad=legend_dict["color_bar_dict"]["pad"],
        aspect=legend_dict["color_bar_dict"]["aspect"],
        fraction=legend_dict["color_bar_dict"]["fraction"],
        ticks=bin_centers,
    )
    cbar.set_ticklabels(figure_dict["bin_labels"], fontsize=figure_dict["tick_font_size"])
    cbar.set_label(figure_dict["colorbar_label"], fontsize=figure_dict["colorbar_title_font_size"])


def plot_map(plot_dict, get_plot_data):
    """
    Main entry point for plotting a map.
    plot_dict: dictionary with plotting parameters
    get_plot_data: user-provided function that returns the required data for plotting
    """
    plot_dict = get_plot_data(plot_dict)
    fig, ax = plt.subplots(subplot_kw={"projection": ccrs.PlateCarree()})
    ax = setup_map_plot(ax, plot_dict)
    plot_base_admins(ax, plot_dict)
    plot_data_admins(ax, plot_dict)
    add_colorbar(fig, ax, plot_dict)
    plt.show()
