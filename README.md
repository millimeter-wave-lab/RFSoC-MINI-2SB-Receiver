# RFSoC MINI 2SB Receiver
This repository contains Simulink models for **(Ideal) Digital Sideband Separation** on RFSoC 4x2 for Southern Millimeter Wave Telescope (or Southern Mini). Python and C++ scripts for initialization, control, and data analysis are included.

## Simulink Models
The `64_bits_models/` and `32_bits_models/` folder contains Simulink designs for FPGA programming. Each model is built using Xilinx System Generator for DSP and targets FPGA boards such as the Zynq UltraScale+ RFSoC. To design the spectrometers, [CASPER toolflow](https://casper-toolflow.readthedocs.io/projects/tutorials/en/latest/tutorials/rfsoc/tut_getting_started.html) must be installed.

### 64 bits models (Experimental Only)
Three 64-bits models were designed and used in laboratory for test ideal sideband separation. These models have a 1.96608 GHz bandwidth and 64-bit BRAMs, and are available for the next spectral resolutions:
- 2048 channels
- 8192 channels
- 16384 channels

### 32 bits models
Due to the 32-bit limitation of the radiotelescope microcontroller (PIC32), this repository includes spectrometer models with 32-bit BRAMs. These models are available for different spectral resolutions:
- 8192 channels
- 16384 channels
- 32768 channels
- 65536 channels (implemented in two separate models due to resource limitations.)

Each model includes:
- 32-bit BRAM blocks for data acquisition, named `synth0_i` and `synth1_i` for the high-resolution spectrometer, and `re_bin_synth0_i` and `re_bin_synth1_i` for the parallel 512-channel spectrometer.
- Reset accumulation control.
- Bits re-quantization blocks.

> **Note:** For the 65536-channel models, the **User IP Clock Rate** in the **RFSoC 4x2** Simulink block **was set to 122.88 MHz**. This setting is required to match the **Required AXI4-Stream Clock Rate** of the **RFDC** block; otherwise, the model will fail to compile.  

## Python Scripts

This repository includes Python scripts for initializing the RFSoC, configuring registers, capturing data, and performing post-processing (e.g., plotting spectra, calculate SRR, etc.). 

| File | Description |
|------|-------------|
| `anim_dss_spectrum_1966mhz.py` | Plots the spectrum in real time for a 1.96608 GHz bandwidth. <br>**Usage:** `python anim_dss_spectrum_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <Data Output Width>` |
| `anim_dss_spectrum_65536ch_1966mhz.py` |Plots the spectrum in real time for 65536-channel models, selects first or second half of the spectrum via `part` argument. <br>**Usage:** `python anim_dss_spectrum_65536ch_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <Data Output Width> <part>` (where `part` = 1 or 2) |
| `sweep_srr_plot_1966mhz.py` | Performs a sweep across the full bandwidth and computes the Sideband Rejection Ratio (SRR). <br>**Usage:** `python sweep_srr_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF Instrument IP address> <Data Output Width>` |
| `sweep_srr_plot_65536ch_1966mhz.py` | Sweeps a portion of the bandwidth and calculates the Sideband Rejection Ratio (SRR) for 65536-channel models. The script selects either the first or second half of the spectrum using the `part` argument. <br>**Usage:** `python sweep_srr_plot_65536ch_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF Instrument IP address> <Data Output Width> <part>` (where `part` = 1 or 2) |
| `sweep_ph_plot_1966mhz.py` | Sweeps across the full bandwidth and calculates phase difference between I and Q outputs. Only works for 64-bits models. <br>**Usage:** `python sweep_ph_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF instrument IP address> <Data Output Width>` |
| `plot_srr_ph_diff.py` | Plots SRR or phase difference from a CSV file. <br>**Usage:** `python plot_srr_ph_diff.py` |
| `plot_srr_65536ch.py` | Plots SRR for 65536-channels spectrometer models. Reads two CSV files corresponding to first and second part of the bandwidth. <br>**Usage:** `python plot_srr_65536ch.py` |
| `test_spec_cnt.py` | Tests the accumulation counter. <br>**Usage:** `python test_spec_cnt.py` |

## Mini Implementation

This section includes Python and C++ scripts used for communication testing and deployment of the RFSoC-based spectrometer system at the Southern Millimeter Wave Telescope (Mini).

### Python Scripts

| File | Description |
|------|-------------|
| `rfsoc4x2_spec_ini.py` | Initializes and programs the RFSoC with the selected spectrometer model. <br>**Usage:** `python rfsoc4x2_spec_ini.py` |
| `cpp_interface.py` | Python interface that repeatedly requests spectra via the C++ client and measures the response time. Results are logged to a `.csv` file. <br>**Usage:** `python cpp_interface.py` |
| `plot.py` | Plots delays recorded during spectrum acquisition requests. <br>**Usage:** `python plot.py` |
| `rfsoc_mini_client.py` | Python client script used in the Mini radiotelescope Data Server. Requests spectra and transmits them to the PIC32 microcontroller. <br>**Usage:** `python rfsoc_mini_client.py` |

### C++ Scripts

| File | Description |
|------|-------------|
| `rfsoc_<n_ch>ch_<mode>_server.cpp` | C++ server that runs on the RFSoC. It waits for incoming client connections and sends spectrum data. Located in the `rfsoc_server` folder. <br><br>**Parameters:**<br>- `n_ch`: number of channels, valid values are `8192`, `16384`, or `32768`.<br>- `mode`: operation mode, either `cal` (calibrated) or `ideal` (ideal model).<br><br>**Note:** For 65536-channel models, use the `32768`-channel server. The bitstream `dss_ideal1_65536ch_32bits_reset_1966mhz_cx.fpg` observes the **first** 32768 channels of the bandwidth, while `dss_ideal2_65536ch_32bits_reset_1966mhz_cx.fpg` observes the **second** 32768 channels. |
| `cpp_socket.cpp` | C++ client that connects to the RFSoC server and requests spectrum data. It is compiled as a Python extension using `pybind11`, enabling integration with Python scripts. |


### Execution Flow

Below is the standard sequence to run the RFSoC spectrometer system:

1. **Program the RFSoC with the spectrometer bitstream**  
   Load the selected spectrometer model onto the RFSoC using the initialization script:

   ```bash
   python rfsoc4x2_spec_ini.py
   ```
2. **Start the RFSoC Server**  
   Connect to the RFSoC via SSH:
   ```bash
   ssh casper@<rfsoc-ip>
   ```
   Then, compile and run the server. The following example uses the 8192-channel server for the ideal model:


   ```bash
   g++ rfsoc_8192ch_ideal_server.cpp -o rfsoc_8192ch_ideal_server

   sudo ./rfsoc_8192ch_ideal_server
3. **Compile the C++ Socket Client**  
   On the control computer, compile:

   ```bash
   c++ -O3 -Wall -shared -std=c++11 -fPIC `python3 -m pybind11 --includes` cpp_socket.cpp -o cpp_socket`python3-config --extension-suffix`
   ```
4. **Run the Python Interface**  
   Choose one of the following scripts depending on the use case:

   - **Laboratory testing interface** – This script repeatedly requests spectra via the C++ client and measures the response time. It logs the delays in a `.csv` file for later analysis.

     ```bash
     python cpp_interface.py
     ```

   - **Mini telescope deployment interface** – This script runs on the Data Server located at the Mini telescope site. It requests spectra from the RFSoC and sends them directly to the PIC32 microcontroller, without logging timing information.

     ```bash
     python rfsoc_mini_client.py
     ```
