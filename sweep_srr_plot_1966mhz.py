import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import casperfpga
import pyvisa
import time
import argparse

def get_vacc_data_power(fpga, nchannels, nfft):

  chunk = nfft//nchannels

  raw1 = np.zeros((nchannels, chunk))
  raw2 = np.zeros((nchannels, chunk))
  
  t_raw = time.time()

  for i in range(nchannels):
    # a = time.time()
    if nfft == 512:
      raw1[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('re_bin_synth0_{:d}'.format((i)),chunk*8,0))
      raw2[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('re_bin_synth1_{:d}'.format((i)),chunk*8,0))
    else:
      raw1[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('synth0_{:d}'.format((i)),chunk*8,0))
      raw2[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('synth1_{:d}'.format((i)),chunk*8,0))
    # print((time.time()-a)*8)
  print(f"Obtención de raw1 y raw2: {(time.time()-t_raw)*1000} ms")
  
  interleave_q = []
  interleave_i = []
  t_sort = time.time()

  for i in range(chunk):
    for j in range(nchannels):
      interleave_q.append(raw1[j,i])
      interleave_i.append(raw2[j,i])

  print(f"Reordenamiento: {(time.time()-t_sort)*1000} ms")

  return np.array(interleave_i, dtype=np.float64), np.array(interleave_q, dtype=np.float64)


def plot_SRR(fpga, instrument, Nfft, bin_step):

  fs = 3932.16/2
  LO = 3000
  SRR = []
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
      spectrum1, spectrum2 = get_vacc_data_power(fpga, nchannels=nchannels, nfft=Nfft)
      # print(time.time()-a)
      diff = 10 * (np.log10(fft.fftshift(spectrum1+1)[-i-1]/fft.fftshift(spectrum2+1)[-i-1]))
      # print(faxis_LSB[-i-1]/1000,diff)
      SRR.append(diff)
      
    for i in range(0, Nfft, bin_step):
      instrument.write(f'FREQ:CENT {faxis_USB[i]}e6')
      time.sleep(0.1)
      
      spectrum1, spectrum2 = get_vacc_data_power(fpga, nchannels=nchannels, nfft=Nfft)
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
        usage='sweep_srr_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF instrument IP address> [options]'
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
        plot_SRR(fpga, instrument, Nfft, 1)
    except KeyboardInterrupt:
        sys.exit()
