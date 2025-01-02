import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import casperfpga
import pyvisa
import time
import argparse

def get_vacc_data_power(fpga, n_outputs, nfft, n_bits):
  """Get the raw data from fpga digital sideband separation spectrometer"""

  bins_out = nfft//n_outputs    # Number of bins for each output

  if n_bits == 64:    # Shared BRAMs data width of 8 bytes (64 bits)
    
    data_width = 8    # 8 bytes (64 bits)

    data_type = 'Q'   # Format character 'unsigned long long'
  
  else:               # Shared BRAMs data width of 4 bytes (32 bits)
    
    data_width = 4    # 4 bytes (32 bits)

    data_type = 'L'   # Format character 'unsigned long'
  

  add_width = bins_out    # Number of "Data Width" words of the implemented BRAM
                          # Must be set to store at least the number of output bins of each bram

  raw1 = np.zeros((n_outputs, bins_out))
  raw2 = np.zeros((n_outputs, bins_out))
  
  for i in range(n_outputs):    # Extract data from BRAMs blocks for each output
    
    if nfft == 512:   # Re_bin spectrum
      raw1[i,:] = struct.unpack(f'>{bins_out}{data_type}',
      fpga.read(f're_bin_synth0_{i}', add_width * data_width, 0))
      raw2[i,:] = struct.unpack(f'>{bins_out}{data_type}', 
      fpga.read(f're_bin_synth1_{i}', add_width * data_width, 0))
    
    else:   # High resolution spectrum
      raw1[i,:] = struct.unpack(f'>{bins_out}{data_type}',
      fpga.read(f'synth0_{i}', add_width * data_width, 0))
      raw2[i,:] = struct.unpack(f'>{bins_out}{data_type}',
      fpga.read(f'synth1_{i}', add_width * data_width, 0))
    
  interleave_q = raw1.T.ravel().astype(np.float64) 
  interleave_i = raw2.T.ravel().astype(np.float64)

  return interleave_i, interleave_q


def plot_SRR(fpga, instrument, Nfft, n_bits, bin_step):
  '''Sweeps frequencies and plots SRR with given options'''

  fs = 3932.16/2    # Bandwidth
  LO = 3000   # Local Oscilator
  SRR = []    # Sideband Rejection Ratio
  try:

    n_outputs = 8

    if_freqs = np.linspace(0, fs, Nfft, endpoint=False)

    faxis_LSB = LO - if_freqs

    faxis_USB = LO + if_freqs
      
    for i in range(0, Nfft, bin_step):
      instrument.write(f'FREQ {faxis_LSB[-i-1]}e6')
      time.sleep(0.1)

      spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)
      diff = 10 * (np.log10(fft.fftshift(spectrum1+1)[-i-1]/fft.fftshift(spectrum2+1)[-i-1]))

      print(faxis_LSB[-i-1]/1000,diff)
      SRR.append(diff)
      
    for i in range(0, Nfft, bin_step):
      instrument.write(f'FREQ {faxis_USB[i]}e6')
      time.sleep(0.1)
      
      spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)
      diff = 10 * (np.log10(fft.fftshift(spectrum2+1)[i]/fft.fftshift(spectrum1+1)[i]))
      
      print(faxis_USB[i]/1000,diff)
      SRR.append(diff)

  except KeyboardInterrupt:
    print("User interruption. Plotting data...")
  
  faxis = np.concatenate((faxis_LSB[::-1][::bin_step], faxis_USB[::bin_step]))[:len(SRR)]

  fig = plt.figure()
  ax = fig.add_subplot(111)
  ax.grid();
  line, = ax.plot(faxis, SRR, '-', color="black")

  plt.xlabel('RF Frequency (MHz)')
  plt.ylabel('SRR (dB)')
  plt.title('Sideband Rejection Ratio')
  ax.set_ylim(-10, 70)

  plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Sweeps frequencies and plots SRR with given options',
        usage='sweep_srr_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF instrument IP address> <Data Output Width>[options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Operation mode: Nfft Size')
    parser.add_argument('rf_instrument', type=str, help='RF instrument IP address')
    parser.add_argument('n_bits', type=int, help='BRAMs data output width')

    parser.add_argument('-l', '--acc_len', type=int, default=2**9,
                        help='Set the number of vectors to accumulate between dumps')
    parser.add_argument('-s', '--skip', action='store_true',
                        help='Skip programming and begin to plot data')
    parser.add_argument('-b', '--fpgfile', type=str, default='',
                        help='Specify the FPG file to load')

    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft
    rf_instrument = args.rf_instrument
    n_bits = args.data_output_width

    # Use your .fpg file
    bitstream = args.fpgfile if args.fpgfile else '8192ch_32bits_reset/dss_ideal_8192ch_32bits_reset_1966mhz_cx.fpg'

    print(f'Connecting to {hostname}...')
    fpga = casperfpga.CasperFpga(hostname)
    time.sleep(0.2)

    if not args.skip:
        print(f'Programming FPGA with {bitstream}...')
        fpga.upload_to_ram_and_program(bitstream)
        print('Done')
    else:
        fpga.get_system_information()
        print('Skip programming FPGA...')

    print('Initializing RFDC block...')    
    fpga.adcs['rfdc'].init()
    c = fpga.adcs['rfdc'].show_clk_files()
    fpga.adcs['rfdc'].progpll('lmk', c[1])
    fpga.adcs['rfdc'].progpll('lmx', c[0])
    time.sleep(1)
    print('Done')

    print('Configuring accumulation period...')
    fpga.write_int('acc_len', args.acc_len)
    # fpga.write_int('acc_len_pic', args.acc_len)
    
    if n_bits == 32:
       fpga.write_int('gain', 2**10)
    time.sleep(1)
    print('Done')

    print('Resetting counters...')
    fpga.write_int('cnt_rst', 1)
    fpga.write_int('cnt_rst', 0)
    time.sleep(1)
    print('Done')

    print('Connecting to instruments...')
    rm = pyvisa.ResourceManager('@py')
    instrument = rm.open_resource(f'TCPIP0::{rf_instrument}::INSTR')
    time.sleep(1)
    print('Done')

    try:
        plot_SRR(fpga, instrument, Nfft, n_bits, 16)
    except KeyboardInterrupt:
        sys.exit()
