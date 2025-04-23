import argparse
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import act
from datetime import timedelta
from waggle.plugin import Plugin
import datetime
import glob



def filter_recent_files(path, file_pattern, plot_day):
    """
    Returns a list of filepaths for NetCDF files from the last given period
    by creating glob patterns based on the current time and a file prefix
    assuming the filename contains a timestamp in specific format information.

    Args:
        path (Path): The directory path to search for files.
        file_prefix (str): The prefix of the filenames (e.g., 'cmscl6001_').

    Returns:
        list: A list of pathlib.Path objects for the NetCDF files found
              from the last hour.
    """
    recent_files = []
    now = datetime.datetime.now()
    if plot_day =='yesterday':
        plot_day = now - timedelta(days=1)
    elif plot_day =='today':
        plot_day= now

    plot_day_str = now.strftime("%Y%m%d")

    # Pattern for files from the beginning of the last hour to the end of the last hour
    glob_pattern = f"{path}/*{plot_day_str}{file_pattern}"
    #glob_pattern = "/cl61/cmscl6001_20230801*.nc"
    logging.info(f'checking files in {glob_pattern}')
    recent_files = glob.glob(glob_pattern)

    return recent_files




def plot_dataset(filepaths):
    if not filepaths:
        logging.warning("No recent NetCDF files found for plotting.")
        return None

    ds = xr.open_mfdataset(filepaths, combine="by_coords")
    logging.info(ds)
    plot_file_name = f'/tmp/cl61_plot_{str(ds["time"].values[-1])}.png'

    variables = ["beta_att", "p_pol", "x_pol"]
    for var in variables:
        if var != "linear_depol_ratio":
            ds = act.corrections.correct_ceil(ds, var_name=var)

    # for plotting, it is better
    ds = ds.assign(range_km=ds['range'] / 1000)
    ds= ds.assign(sky_condition_cloud_layer_heights_km = ds['sky_condition_cloud_layer_heights']/1000)
    ds['range_km'].attrs['units'] = 'km' 
    ds = ds.swap_dims({'range': 'range_km'})

    fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(10, 10), sharex=True)
    ylim = (0, 8)

    date_title = f"CROCUS CL61: {np.datetime_as_string(ds['time'].values[0], unit='s')}"
    fig.suptitle(date_title, fontsize=16)

    ds["beta_att"].plot(ax=axes[0], x="time", y="range_km", cmap="PuBuGn", robust=True)
    #ds['sky_condition_cloud_layer_heights'].plot.line(ax=axes[0], x='time', add_legend=False,color='white', linestyle=':')
    axes[0].set_title("Attenuated Volume Backscatter Coefficient")
    axes[0].set_xlabel("Time [UTC]")
    axes[0].set_ylabel("Height [km]")
    axes[0].set_ylim(ylim)

    ds["p_pol"].plot(ax=axes[1], x="time", y="range_km", cmap="viridis", robust=True, vmin=-8, vmax=8)
    ds['sky_condition_cloud_layer_heights_km'].plot.line(ax=axes[1], x='time', add_legend=False)
    axes[1].set_title("Parallel-Polarized Component")
    axes[1].set_xlabel("Time [UTC]")
    axes[1].set_ylabel("Height [km]")
    axes[1].set_ylim(ylim)

    ds["x_pol"].plot(ax=axes[2], x="time", y="range_km", cmap="viridis", robust=True, vmin=-8, vmax=8)
    ds['sky_condition_cloud_layer_heights_km'].plot.line(ax=axes[2], x='time', add_legend=False)
    axes[2].set_title("Cross-Polarized Component")
    axes[2].set_xlabel("Time [UTC]")
    axes[2].set_ylabel("Height [km]")
    axes[2].set_ylim(ylim)

    ds["linear_depol_ratio"].plot(ax=axes[3], x="time", y="range_km", cmap="Spectral_r", vmin=0, vmax=0.7, robust=True)
    #ds['sky_condition_cloud_layer_heights'].plot.line(ax=axes[3], x='time', add_legend=False, color='white', linestyle=':')
    axes[3].set_title("Linear Depolarization Ratio")
    axes[3].set_xlabel("Time [UTC]")
    axes[3].set_ylabel("Height [km]")
    axes[3].set_ylim(ylim)

    plt.tight_layout()
    plt.savefig(plot_file_name)
    plt.close()
    return plot_file_name



def main(args):
    path = Path(args.dir_path)
    if not path.is_dir():
        logging.error(f"The provided path '{args.dir_path}' is not a valid directory.")
        return 1

    with Plugin() as plugin:
        logging.info(f"Looking for {args.period}'s files ...")
        recent_files = filter_recent_files(path, args.file_pattern, args.period)
        logging.info(recent_files)

        if not recent_files:
            logging.info("No recent files found.")
            return 0

        logging.info(f"Found {len(recent_files)} recent files. Plotting...")
        plot_file = plot_dataset(recent_files)

        if plot_file:
            logging.info(f"Uploading plot {plot_file}")
            plugin.upload_file(plot_file)
        else:
            logging.warning("Plotting failed or no data to plot.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot and upload NetCDF data from last hour.")
    parser.add_argument("--DEBUG", action="store_true", help="Enable debug logging.")
    parser.add_argument("--dir-path", type=str, default="/cl61/", help="Directory path to search for files.")
    parser.add_argument("--file-pattern", type=str, default="*.nc", help="File pattern to match.")
    parser.add_argument("--period", type=str, default="yesterday", choices=["today", "yesterday"], help="today/yesterday")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.DEBUG else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    exit(main(args))
