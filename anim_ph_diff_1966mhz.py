import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import casperfpga
import argparse

def get_vacc_data_power(fpga, nchannels, nfft):
  """Get the raw data from fpga digital spectrometer"""

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

def anim_phase_diff(fpga, Nfft):

    print(Nfft)
    fs = 3932.16/2
    nchannels = 8

    faxis = np.linspace(0, fs, Nfft, endpoint=False)
    re, im = get_vacc_data_re_im(fpga, nchannels=nchannels, nfft=Nfft)
    
    comp = re + 1j*im

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.grid();

    line, = ax.plot(faxis, np.angle(fft.fftshift(comp), deg=True), '-', color="black")

    ax.set_xlabel('RF Frequency (MHz)')
    ax.set_ylabel('Phase Difference in Degrees')
    ax.set_title('Measured Phase Difference between IF Outputs')
    ax.set_ylim(-180, 180)

    def update(frame, *fargs):

      re, im = get_vacc_data_re_im(fpga, nchannels=nchannels, nfft=Nfft)
      comp = re + 1j*im
      line.set_ydata(np.angle(fft.fftshift(comp),deg=True))


    v = anim.FuncAnimation(fig, update, frames=1, repeat=True, fargs=None, interval=10)
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Shows real time phase difference between IF Outputs with given options',
        usage='anim_ph_diff_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> [options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Operation mode: Nfft Size')

    parser.add_argument('-l', '--acc_len', type=int, default=512,
                        help='Set the number of vectors to accumulate between dumps. Default is 2*(2^28)/2048')
    parser.add_argument('-s', '--skip', action='store_true',
                        help='Skip programming and begin to plot data')
    parser.add_argument('-b', '--fpgfile', type=str, default='',
                        help='Specify the FPG file to load')

    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft

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

    try:
        anim_phase_diff(fpga, Nfft)
    except KeyboardInterrupt:
        sys.exit()
