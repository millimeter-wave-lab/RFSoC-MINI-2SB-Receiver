import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import casperfpga
import pyvisa
import argparse

def get_vacc_data_re_im(fpga, n_outputs, nfft, n_bits):
  """Get the raw data from fpga digital correlator"""

  bins_out = nfft//n_outputs    # Number of bins for each output

  if n_bits == 64:    # Shared BRAMs data width of 8 bytes (64 bits)
    
    data_width = 8    # 8 bytes (64 bits)

    data_type = 'q'   # Format character 'long long'
  
  else:               # Shared BRAMs data width of 4 bytes (32 bits)
    
    data_width = 4    # 4 bytes (32 bits)

    data_type = 'l'   # Format character 'long'
  

  add_width = bins_out    # Number of "Data Width" words of the implemented BRAM
                          # Must be set to store at least the number of output bins of each bram

  raw1 = np.zeros((n_outputs, bins_out))
  raw2 = np.zeros((n_outputs, bins_out))
    
  for i in range(n_outputs):    # Extract data from BRAMs blocks for each output
    
    if nfft == 512:   # Re_bin
      raw1[i,:] = struct.unpack(f'>{bins_out}{data_type}',
      fpga.read(f're_bin_ab_re{i}', add_width * data_width, 0))
      raw2[i,:] = struct.unpack(f'>{bins_out}{data_type}', 
      fpga.read(f're_bin_ab_im{i}', add_width * data_width, 0))
    
    else:   # High resolution
      raw1[i,:] = struct.unpack(f'>{bins_out}{data_type}',
      fpga.read(f'ab_re{i}', add_width * data_width, 0))
      raw2[i,:] = struct.unpack(f'>{bins_out}{data_type}',
      fpga.read(f'ab_im{i}', add_width * data_width, 0))

  re = raw1.T.ravel().astype(np.float64)
  im = raw2.T.ravel().astype(np.float64)

  return re, im

def plot_phase_diff(fpga, instrument, Nfft, n_bits, bin_step):
  '''Sweeps frequencies and plots phase difference with given options'''

  fs = 3932.16/2    # Bandwidth
  LO = 3000   # Local Oscilator
  phase = []    # Phase Difference
  try:

    n_outputs = 8

    if_freqs = np.linspace(0, fs, Nfft, endpoint=False)

    faxis_LSB = LO - if_freqs

    faxis_USB = LO + if_freqs

    for i in range(0, Nfft, bin_step):
      instrument.write(f'FREQ {faxis_LSB[-i-1]}e6')
      time.sleep(0.1)

      re, im = get_vacc_data_re_im(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)
      comp = fft.fftshift(re + 1j*im)
      angle = np.angle(comp[-1-i], deg=True)

      print(faxis_LSB[-i-1]/1000, angle)
      phase.append(angle)

    for i in range(0, Nfft, bin_step):
      instrument.write(f'FREQ {faxis_USB[i]}e6')
      time.sleep(0.1)

      re, im = get_vacc_data_re_im(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)
      comp = fft.fftshift(re + 1j*im)
      angle = np.angle(comp[i], deg=True)

      print(faxis_USB[i]/1000, angle)
      phase.append(angle)      

  except KeyboardInterrupt:
    print("User interruption. Plotting data...")

  faxis = np.concatenate((faxis_LSB[::-1][::bin_step], faxis_USB[::bin_step]))[:len(phase)]

  fig = plt.figure()
  ax = fig.add_subplot(111)
  ax.grid();
  line, = ax.plot(faxis, phase, '-', color="black")

  ax.set_xlabel('RF Frequency (MHz)')
  ax.set_ylabel('Phase Difference in Degrees')
  ax.set_title('Measured Phase Difference between IF Outputs')
  ax.set_ylim(-180, 180)

  plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Sweeps frequencies and plots phase difference with given options',
        usage='python sweep_ph_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF instrument IP address> <Data Output Width> [options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Operation mode: Nfft Size')
    parser.add_argument('rf_instrument', type=str, help='RF instrument IP address')
    parser.add_argument('data_output_width', type=int, help='BRAMs data output width')

    parser.add_argument('-l', '--acc_len', type=int, default=2**10,
                        help='Set the number of vectors to accumulate between dumps. Default is 2*(2^28)/2048')
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
    time.sleep(1)

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
        plot_phase_diff(fpga, instrument, Nfft, n_bits, 32)
    except KeyboardInterrupt:
        sys.exit()