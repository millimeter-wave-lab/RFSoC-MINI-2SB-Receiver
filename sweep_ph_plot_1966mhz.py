import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import casperfpga
import pyvisa
import argparse

def get_vacc_data_re_im(fpga, nchannels, nfft, re_bin):
  
  chunk = nfft//nchannels

  raw1 = np.zeros((nchannels, chunk))
  raw2 = np.zeros((nchannels, chunk))

  for i in range(nchannels):
    if re_bin:
      raw1[i,:] = struct.unpack('>{:d}q'.format(chunk), fpga.read('re_bin_ab_re{:d}'.format((i)),chunk*8,0))
      raw2[i,:] = struct.unpack('>{:d}q'.format(chunk), fpga.read('re_bin_ab_im{:d}'.format((i)),chunk*8,0))
    else:
      raw1[i,:] = struct.unpack('>{:d}q'.format(chunk), fpga.read('ab_re{:d}'.format((i)),chunk*8,0))
      raw2[i,:] = struct.unpack('>{:d}q'.format(chunk), fpga.read('ab_im{:d}'.format((i)),chunk*8,0))  

  re = []
  im = []
  for i in range(chunk):
    for j in range(nchannels):
      re.append(raw1[j,i])
      im.append(raw2[j,i])

  return np.array(re, dtype=np.float64), np.array(im, dtype=np.float64)

def plot_phase_diff(fpga, instrument, re_bin):

  fs = 3932.16/2
  LO = 3000
  phase = []
  try:

    if re_bin:
      Nfft = 2**9
    else:
      Nfft = 2**13

    nchannels = 8

    if_freqs = np.linspace(0, fs, Nfft, endpoint=False)

    faxis_LSB = LO - if_freqs

    faxis_USB = LO + if_freqs

    for i in range(Nfft):
      instrument.write(f'FREQ {faxis_LSB[-i-1]}e6')
      time.sleep(0.1)

      re, im = get_vacc_data_re_im(fpga, nchannels=nchannels, nfft=Nfft, re_bin=re_bin)
      comp = fft.fftshift(re + 1j*im)
      angle = np.angle(comp[-1-i], deg=True)
      print(faxis_LSB[-i-1]/1000, angle)
      phase.append(angle)

    for i in range(Nfft):
      instrument.write(f'FREQ {faxis_USB[i]}e6')
      time.sleep(0.1)

      re, im = get_vacc_data_re_im(fpga, nchannels=nchannels, nfft=Nfft, re_bin=re_bin)
      comp = fft.fftshift(re + 1j*im)
      angle = np.angle(comp[i], deg=True)
      print(faxis_USB[i]/1000, angle)
      phase.append(angle)      

  except KeyboardInterrupt:
    print("User interruption. Plotting data...")

  faxis = np.concatenate((faxis_LSB[::-1], faxis_USB))[:len(phase)]

  fig = plt.figure()
  ax = fig.add_subplot(111)
  ax.grid();
  line, = ax.plot(faxis, phase, '-', color="black")

  ax.set_xlabel('RF Frequency (MHz)')
  ax.set_ylabel('Phase Difference in Degrees')
  ax.set_title('Measured Phase Difference between IF Outputs')
  ax.set_ylim(-200, 200)

  plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Sweeps frequencies and plots phase difference with given options',
        usage='sweep_ph_plot_1966mhz.py <HOSTNAME_or_IP> cx|real <RF instrument IP address> [options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('re_bin', type=str, choices=['pic', 'ds'], help='Operation mode: "pic" or "ds"')
    parser.add_argument('rf_instrument', type=str, help='RF instrument IP address')

    parser.add_argument('-l', '--acc_len', type=int, default=4*1024,
                        help='Set the number of vectors to accumulate between dumps. Default is 2*(2^28)/2048')
    parser.add_argument('-s', '--skip', action='store_true',
                        help='Skip programming and begin to plot data')
    parser.add_argument('-b', '--fpgfile', type=str, default='',
                        help='Specify the FPG file to load')

    args = parser.parse_args()

    hostname = args.hostname
    re_bin = args.re_bin
    rf_instrument = args.rf_instrument

    if re_bin == 'pic':
        re_bin_mode = 1
    elif re_bin == 'ds':
        re_bin_mode = 0
    else:
        print('Operation mode not recognized, must be "pic" or "ds"')
        sys.exit()

    bitstream = args.fpgfile if args.fpgfile else '8192ch/dss_ideal_1966mhz_cx_8192ch.fpg'

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

    print('Configuring accumulation period...')
    fpga.write_int('acc_len', args.acc_len)
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
        plot_phase_diff(fpga, instrument, re_bin_mode)
    except KeyboardInterrupt:
        sys.exit()
