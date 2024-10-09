import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import casperfpga
import argparse

def get_vacc_data_power(fpga, nchannels, nfft, re_bin):
  """Get the raw data from fpga digital spectrometer"""
  
  chunk = nfft//nchannels

  raw1 = np.zeros((nchannels, chunk))
  raw2 = np.zeros((nchannels, chunk))
  
  for i in range(nchannels):
    if re_bin:
      raw1[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('re_bin_synth0_{:d}'.format((i)),chunk*8,0))
      raw2[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('re_bin_synth1_{:d}'.format((i)),chunk*8,0))
    else:
      raw1[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('synth0_{:d}'.format((i)),chunk*8,0))
      raw2[i,:] = struct.unpack('>{:d}Q'.format(chunk), fpga.read('synth1_{:d}'.format((i)),chunk*8,0))

  interleave_q = []
  interleave_i = []
  for i in range(chunk):
    for j in range(nchannels):
      interleave_q.append(raw1[j,i])
      interleave_i.append(raw2[j,i])

  return np.array(interleave_i, dtype=np.float64), np.array(interleave_q, dtype=np.float64)


def plot_spectrum(fpga, re_bin):

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1) 
    ax1.grid()
    ax2.grid()
    ax3.grid()

    if re_bin:
      Nfft = 2**9
    else:
      Nfft = 2**13

    print(Nfft)
    fs = 3932.16 / 2
    nchannels = 8

    faxis = np.linspace(0,fs, Nfft ,endpoint=False)

    spectrum1, spectrum2 = get_vacc_data_power(fpga, nchannels=nchannels, nfft=Nfft, re_bin=re_bin)

    line1, = ax1.plot(faxis, 10 * np.log10(fft.fftshift(spectrum1+1)), '-')
    ax1.set_xlabel('Frequency (MHz)')
    ax1.set_ylabel('Power (dB arb.)')
    ax1.set_title('LSB')

    ax1.set_ylim([0, 200]) 

    line2, = ax2.plot(faxis, 10 * np.log10(fft.fftshift(spectrum2+1)), '-')
    ax2.set_xlabel('Frequency (MHz)')
    ax2.set_ylabel('Power (dB arb.)')
    ax2.set_title('USB')

    ax2.set_ylim([0, 200])  

    line3, = ax3.plot(faxis, np.abs(10 * np.log10(fft.fftshift(spectrum1+1)/fft.fftshift(spectrum2+1))), '-')
    ax3.set_xlabel('Frequency (MHz)')
    ax3.set_ylabel('SRR (dB)')
    ax3.set_title('Sideband Rejection Ratio')

    ax3.set_ylim([-10, 40])  
    
    def update(frame, *fargs):

        spectrum1, spectrum2 = get_vacc_data_power(fpga, nchannels=nchannels, nfft=Nfft, re_bin=re_bin)
        line1.set_ydata(10 * np.log10(fft.fftshift(spectrum1+1)))
        line2.set_ydata(10 * np.log10(fft.fftshift(spectrum2+1)))
        line3.set_ydata(np.abs(10 * np.log10(fft.fftshift(spectrum1+1)/fft.fftshift(spectrum2+1))))

    v = anim.FuncAnimation(fig, update, frames=1, repeat=True, fargs=None, interval=10)
    plt.tight_layout() 
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Shows real time sidebands spectrums and SRR with given options',
        usage='sweep_ph_plot_1966mhz.py <HOSTNAME_or_IP> cx|real [options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('re_bin', type=str, choices=['pic', 'ds'], help='Operation mode: "pic" or "ds"')

    parser.add_argument('-l', '--acc_len', type=int, default=4*1024,
                        help='Set the number of vectors to accumulate between dumps. Default is 2*(2^28)/2048')
    parser.add_argument('-s', '--skip', action='store_true',
                        help='Skip programming and begin to plot data')
    parser.add_argument('-b', '--fpgfile', type=str, default='',
                        help='Specify the FPG file to load')

    args = parser.parse_args()

    hostname = args.hostname
    re_bin = args.re_bin

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

    try:
        plot_spectrum(fpga, re_bin_mode)
    except KeyboardInterrupt:
        sys.exit()
