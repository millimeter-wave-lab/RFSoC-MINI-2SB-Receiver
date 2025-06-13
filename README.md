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
- 2038 channels
- 8192 channels
- 16384 channels
## 🐍 Python Scripts

This repository includes Python scripts for initializing the FPGA, configuring registers, capturing data, and performing post-processing (e.g., plotting spectra).

### Mini Implementation

| File | Description |
|------|-------------|
| `simple_bram_vacc.slx` | Vector accumulator using BRAM. Useful for spectral accumulation in DSP pipelines. |
| `spectrometer_model.slx` | Top-level spectrometer model including ADC interface, FFT processing, and memory storage. |
| `adc_capture.slx` | Minimal setup to capture raw ADC data from the FPGA and stream it out. |

Before running the scripts, install the dependencies:

```bash
pip install -r requirements.txt
