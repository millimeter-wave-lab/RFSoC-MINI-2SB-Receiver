# RFSoC MINI 2SB Receiver
This repository contains Simulink models for **(Ideal) Digital Sideband Separation** on RFSoC 4x2 for Southern Millimeter Wave Telescope (or Southern Mini). Python and C++ scripts for initialization, control, and data analysis are included.

## 🧠 Simulink Models
The `32_bits_models/` and `64_bits_models/` folder contains Simulink designs for FPGA programming. Each model is built using [Xilinx System Generator for DSP] and targets FPGA boards such as the Zynq UltraScale+ RFSoC. To design the spectrometers, [CASPER toolflow](https://casper-toolflow.readthedocs.io/projects/tutorials/en/latest/tutorials/rfsoc/tut_getting_started.html) must be installed.

### 32 bits models
Due to the 32-bit limitation of the radiotelescope microcontroller (PIC32), this repository includes spectrometer models with a 1.96608 GHz bandwidth and 32-bit BRAMs. These models are available for different spectral resolutions:
- 8192 channels
- 16384 channels
- 32768 channels
- 65536 channels (implemented in two separate models due to resource constraints)

Each model includes:
- 32-bits BRAM blocks for data acquisition.
- Reset accumulation control.
- Bits re-quantization blocks.

> 🔧 **Note:** For the 32768 and 65536 channel models, the User IP Clock Rate in the RFSoC 4x2 Simulink block was reduced to 122.88 MHz to adjust timing and resource constraints.

### 64 bits models (Experimental Only)
There is also three 64-bits models designed and used in laboratory for test ideal sideband separation. These models are available for the next spectral resolutions:
- 2048 channels
- 8192 channels
- 16384 channels
## 🐍 Python Scripts

This repository includes Python scripts for initializing the RFSoC, configuring registers, capturing data, and performing post-processing (e.g., plotting spectra). 

| File | Description |
|------|-------------|
| `anim_dss_spectrum_1966mhz.py` | Plots the spectrum in real time for a 1.96608 GHz bandwidth. <br>**Usage:** `python anim_dss_spectrum_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <Data Output Width> [options]` |
| `anim_dss_spectrum_65536ch_1966mhz.py` | Real-time spectrum plotter for 65536-channel models, selects first or second half of the spectrum via `part` argument. <br>**Usage:** `python anim_dss_spectrum_65536ch_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <Data Output Width> <part>` (where `part` = 1 or 2) |
| `sweep_srr_plot_1966mhz.py` | Performs a sweep across the full bandwidth and computes the Sideband Rejection Ratio (SRR). <br>**Usage:** `python sweep_srr_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF Instrument IP address> <Data Output Width> [options]` |
| `sweep_ph_plot_1966mhz.py` | Sweeps across the full bandwidth and calculates phase difference. <br>**Usage:** `python sweep_ph_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF instrument IP address> <Data Output Width> [options]` |
| `plot_srr_ph_diff.py` | Plots SRR or phase difference from a CSV file. <br>**Usage:** `python plot_srr_ph_diff.py` |
| `test_spec_cnt.py` | Tests the accumulation counter. <br>**Usage:** `python test_spec_cnt.py` |
