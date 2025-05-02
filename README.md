# CL61 Ceilometer Data PScript
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) ![Version](https://img.shields.io/badge/version-0.25.5.2-blue)


Process, visualize, and upload data from a CL61 ceilometer on a Waggle node. It searches for NetCDF data files from a given period (today or yesterday) generates plot visualizing attenuated backscatter, polarization components, depolarization ratio and uploads the image. Optionally uploads the generated plots and combined NetCDF files via the Waggle Plugin interface to Beehive.

## Overview
A Waggle Edge App, typically runs in a Docker container managed by Kubernetes on a Waggle node. 

1.  **Scan:** Look for Vaisala CL61 NetCDF data files (`.nc`) in a specified directory (`--dir-path`).
2.  **Filter:** Select files based on a time period relative to the current time (`--period`: `last_hour`, `today`, `yesterday`).
3.  **Process:** Read the selected files using `xarray`, perform necessary calculations (e.g., log10 of backscatter), and combine them into a single dataset.
4.  **Plot:** Generate a time-height plot using `matplotlib` showing Attenuated Volume Backscatter Coefficient and Linear Depolarization Ratio. Cloud base heights detected by the instrument are overlaid.
5.  **Save (Optional):** Create a new NetCDF file containing the combined data for the selected period (`--upload_nc`).
6.  **Upload:** Utilize the `waggle.plugin` library to upload the generated plot image (`.png`) and optionally the combined NetCDF file (`.nc`) to the Waggle Beehive data platform.

---

## Installation

As this is intended as a Waggle Edge App, installation involves building the Docker container defined by `Dockerfile`.

### Example: Plot last hour's data from local ./data directory
```python app.py --file_prefix vaisalacl61_anl_ --dir-path ./data --period last_hour```

### Example: Process today's data, skip plot, save combined NC file (no Waggle upload)
```bash
python app.py --file_prefix vaisalacl61_anl_ --dir-path ./data --period today --upload_nc --skip_plot
```

```bash
sudo pluginctl build . -t ${IMAGE_NAME}

sudo pluginctl run \
    -n cl61-run-test \
    --selector zone=core \
    --resource request.memory=1Gi,limit.memory=3Gi \
    -v /path/on/node/to/data:/cl61/ \
    ${IMAGE_NAME} \
    -- \
    --file_prefix vaisalacl61_anl_ \
    --period last_hour \
    --upload_nc
```

This code is developed for the CROCUS measurement strategy at Argonne National Laboratory.
For more instruments, codes and data analysis check our [Instrument Cookbooks](https://crocus-urban.github.io/instrument-cookbooks/)