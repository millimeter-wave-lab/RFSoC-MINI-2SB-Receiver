import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import casperfpga
import pyvisa
import argparse

def get_vacc_data_re_im(fpga, nchannels, nfft):
  
  chunk = nfft//nchannels

  raw1 = np.zeros((nchannels, chunk))
  raw2 = np.zeros((nchannels, chunk))

  for i in range(nchannels):

    if nfft == 512:
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

def plot_phase_diff(fpga, instrument, Nfft, bin_step):

  fs = 3932.16/2
  LO = 3000
  phase = []
  try:

    print(Nfft)
    nchannels = 8

    if_freqs = np.linspace(0, fs, Nfft, endpoint=False)

    faxis_LSB = LO - if_freqs

    faxis_USB = LO + if_freqs

    for i in range(0, Nfft, bin_step):
      instrument.write(f'FREQ:CENT {faxis_LSB[-i-1]}e6')
      time.sleep(0.1)

      # a = time.time()
      re, im = get_vacc_data_re_im(fpga, nchannels=nchannels, nfft=Nfft)
      # print(time.time()-a)
      comp = fft.fftshift(re + 1j*im)
      angle = np.angle(comp[-1-i], deg=True)
      print(faxis_LSB[-i-1]/1000, angle)
      phase.append(angle)

    for i in range(0, Nfft, bin_step):
      instrument.write(f'FREQ:CENT {faxis_USB[i]}e6')
      time.sleep(0.1)

      re, im = get_vacc_data_re_im(fpga, nchannels=nchannels, nfft=Nfft)
      comp = fft.fftshift(re + 1j*im)
      angle = np.angle(comp[i], deg=True)
      # print(faxis_USB[i]/1000, angle)
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
  ax.set_ylim(-200, 200)

  plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Sweeps frequencies and plots phase difference with given options',
        usage='sweep_ph_plot_1966mhz.py <HOSTNAME_or_IP> cx|real <RF instrument IP address> [options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Operation mode: Nfft Size')
    parser.add_argument('rf_instrument', type=str, help='RF instrument IP address')

    parser.add_argument('-l', '--acc_len', type=int, default=512,
                        help='Set the number of vectors to accumulate between dumps. Default is 2*(2^28)/2048')
    parser.add_argument('-s', '--skip', action='store_true',
                        help='Skip programming and begin to plot data')
    parser.add_argument('-b', '--fpgfile', type=str, default='',
                        help='Specify the FPG file to load')

    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft
    rf_instrument = args.rf_instrument
    
    if Nfft == 512:
      bitstream = args.fpgfile if args.fpgfile else '16384ch/dss_ideal_1966mhz_cx_16384ch.fpg'

    else:
      bitstream = args.fpgfile if args.fpgfile else f'{Nfft}ch/dss_ideal_1966mhz_cx_{Nfft}ch.fpg'

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
        plot_phase_diff(fpga, instrument, Nfft, 16)
    except KeyboardInterrupt:
        sys.exit()
