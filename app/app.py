import argparse
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from datetime import timedelta
from waggle.plugin import Plugin
import datetime
import glob
import timeout_decorator
import os
from pandas import to_datetime


def filter_recent_files(path, file_pattern, period):
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

    now = datetime.datetime.now()

    if period == 'last_hour':
        start_time = now - datetime.timedelta(hours=1)
        date_str = start_time.strftime("%Y%m%d_%H")  # e.g., 2025042914
        glob_pattern = f"{path}/*{date_str}*{file_pattern}"
    elif period == 'today':
        date_str = now.strftime("%Y%m%d")  # e.g., 20250429
        glob_pattern = f"{path}/*{date_str}{file_pattern}"
    elif period == 'yesterday':
        yesterday = now - datetime.timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")  # e.g., 20250428
        glob_pattern = f"{path}/*{date_str}{file_pattern}"
    else:
        raise ValueError(f"Unsupported period: {period}")

    logging.info(f"Searching files with pattern: {glob_pattern}")

    recent_files = glob.glob(glob_pattern)
    recent_files.sort()

    return recent_files


def read_files_ds(filepaths):
    if not filepaths:
        logging.warning("No recent NetCDF files found for plotting.")
        return None
    
    logging.info("reading data in xarray...")
    ds = xr.open_mfdataset(filepaths, concat_dim='time', combine='nested')
    ds = ds.sortby("time")
    logging.info(ds)

    # copied from ACT
    var_name = 'beta_att'
    data = ds[var_name].data
    data[data <= 0] = 1e-7
    data = np.log10(data)

    ds[var_name].values = data
    if 'units' in ds[var_name].attrs:
        ds[var_name].attrs['units'] = 'log(' + ds[var_name].attrs['units'] + ')'
    else:
        ds[var_name].attrs['units'] = 'log(unknown)'
    
    return ds






def ds_to_netcdf(ds, args, outdir='/tmp/'):
    timestamp = to_datetime(ds['time'].values[0])
    # Then, you can use strftime on the Timestamp object
    date_str = timestamp.strftime("%Y%m%d-%H")

    time_units = f"seconds since {date_str} 00:00:00"

    encoding = {
    "time": {
        "units": time_units,
        "calendar": "standard",
        "dtype": "float64",
        }
    }
    output_path = os.path.join(outdir, f"{args.file_prefix}{date_str}0000.nc")
    output_path = f'/tmp/cl61_plot_{str(ds["time"].values[-1])}.png'
    ds.to_netcdf(output_path, encoding=encoding)

    return output_path


@timeout_decorator.timeout(300, timeout_exception=TimeoutError)
def plot_dataset(ds, args):

    # for plotting, it is better
    ds = ds.assign(range_km=ds['range'] / 1000)
    ds= ds.assign(sky_condition_cloud_layer_heights_km = ds['sky_condition_cloud_layer_heights']/1000)
    ds['range_km'].attrs['units'] = 'km' 
    ds = ds.swap_dims({'range': 'range_km'})

    logging.info("plotting...")
    plot_file_name = f'/tmp/cl61_plot_{str(ds["time"].values[-1])}.png'
    fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(args.plot_size, args.plot_size), sharex=True)

    ylim = (0, args.plot_height)

    date_title = f"{args.file_prefix}{args.period} {np.datetime_as_string(ds['time'].values[0], unit='s')}"
    fig.suptitle(date_title, fontsize=12)

    ds["beta_att"].plot(ax=axes[0], x="time", y="range_km", cmap="PuBuGn", robust=True)
    #ds['sky_condition_cloud_layer_heights'].plot.line(ax=axes[0], x='time', add_legend=False,color='white', linestyle=':')
    plot_cloud_heights(axes[0], ds)
    axes[0].set_title("Attenuated Volume Backscatter Coefficient")
    axes[0].set_xlabel("Time [UTC]")
    axes[0].set_ylabel("Height [km]")
    axes[0].set_ylim(ylim)

    #ds["p_pol"].plot(ax=axes[1], x="time", y="range_km", cmap="viridis", robust=True, vmin=-8, vmax=8)
    #ds['sky_condition_cloud_layer_heights_km'].plot.line(ax=axes[1], x='time', add_legend=False)
    #axes[1].set_title("Parallel-Polarized Component")
    #axes[1].set_xlabel("Time [UTC]")
    #axes[1].set_ylabel("Height [km]")
    #axes[1].set_ylim(ylim)

    #ds["x_pol"].plot(ax=axes[2], x="time", y="range_km", cmap="viridis", robust=True, vmin=-8, vmax=8)
    #ds['sky_condition_cloud_layer_heights_km'].plot.line(ax=axes[2], x='time', add_legend=False)
    #axes[2].set_title("Cross-Polarized Component")
    #axes[2].set_xlabel("Time [UTC]")
    #axes[2].set_ylabel("Height [km]")
    #axes[2].set_ylim(ylim)

    ds["linear_depol_ratio"].plot(ax=axes[1], x="time", y="range_km", cmap="Spectral_r", vmin=0, vmax=0.7, robust=True)
    plot_cloud_heights(axes[1], ds)
    #ds['sky_condition_cloud_layer_heights'].plot.line(ax=axes[3], x='time', add_legend=False, color='white', linestyle=':')
    axes[1].set_title("Linear Depolarization Ratio")
    axes[1].set_xlabel("Time [UTC]")
    axes[1].set_ylabel("Height [km]")
    axes[1].set_ylim(ylim)

    plt.tight_layout()
    plt.savefig(plot_file_name)
    plt.close()
    return plot_file_name




def plot_cloud_heights(ax, ds, color='black'):
    """
    Plots cloud layer heights as small white '~' scatter markers.
    """
    if 'sky_condition_cloud_layer_heights_km' not in ds:
        return

    cloud_heights = ds['sky_condition_cloud_layer_heights_km'].values
    times = ds['time'].values

    # Flatten if it's a 2D array: (time, layers)
    if len(cloud_heights.shape) == 2:
        times = np.repeat(times, cloud_heights.shape[1])
        heights = cloud_heights.flatten()
    else:
        heights = cloud_heights
        times = np.tile(times, 1)

    # Filter valid points
    mask = ~np.isnan(heights)
    ax.scatter(
        times[mask],
        heights[mask],
        marker=1,
        c=color,
        s=5,
        linewidths=0.2
    )



def main(args):
    path = Path(args.dir_path)
    if not path.is_dir():
        logging.error(f"The provided path '{args.dir_path}' is not a valid directory.")
        return 1


    with Plugin() as plugin:
        try:
            logging.info(f"Looking for {args.period}'s files ...")
            recent_files = filter_recent_files(path, args.file_pattern, args.period)
            logging.info(recent_files)

            if not recent_files:
                logging.info("No recent files found.")
                plugin.publish("error", "No recent files found.")
                return 0

            logging.info(f"Found {len(recent_files)} recent files.")
            plugin.publish("status", f"Found {len(recent_files)} recent files.")
            
            ds = read_files_ds(recent_files)
            nc_file = ds_to_netcdf(ds, args)
            if nc_file:
                logging.info(f"Uploading netcdf {nc_file}")
                plugin.upload_file(nc_file)
            else:
                logging.warning
                plugin.publish("error", "Netcdf creation failed or no data.")

            plot_file = plot_dataset(ds, args)
            if plot_file:
                logging.info(f"Uploading plot {plot_file}")
                plugin.upload_file(plot_file)
            else:
                logging.warning
                plugin.publish("error", "Plotting failed or no data to plot.")

        except Exception as e:
            logging.exception(e)
            plugin.publish("error", "Unexpected Error")
            return 2



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot and upload NetCDF data from last hour.")
    parser.add_argument("--DEBUG", action="store_true", help="Enable debug logging.")
    parser.add_argument("--dir-path", type=str, default="/cl61/", help="Directory path to search for files.")
    parser.add_argument("--file-pattern", type=str, default="*.nc", help="File pattern to match.")
    parser.add_argument("--period", type=str, default="last_hour", choices=["today", "yesterday", "last_hour"], help="today/yesterday/last_hour")
    parser.add_argument("--plot_size", type=str, default=8, help="plot size square.")
    parser.add_argument("--plot_height", type=int, default=8, help="plot max height range in km.")
    parser.add_argument("--file_prefix", type=str, required=True, help="crocus-neiu-ceil-a1-")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.DEBUG else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    exit(main(args))
