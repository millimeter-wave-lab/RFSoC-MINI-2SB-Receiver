import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import casperfpga
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

def plot_spectrum(fpga, Nfft, n_bits):

    # fig, (ax1, ax2, ax3) = plt.subplots(3, 1) 
    fig, (ax1, ax2) = plt.subplots(1, 2) 
    ax1.grid()
    ax2.grid()
    # ax3.grid()

    print(Nfft)
    fs = 3932.16 / 2
    n_outputs = 8

    faxis = np.linspace(0,fs, Nfft ,endpoint=False)

    spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)

    line1, = ax1.plot(faxis, 10 * np.log10(fft.fftshift(spectrum1+1)), '-')
    ax1.set_xlabel('Frequency (MHz)')
    ax1.set_ylabel('Power (dB arb.)')
    ax1.set_title('LSB')

    # ax1.axvline((3-1.10712)*1000, color = "red")
    ax1.set_ylim([0, 150]) 

    line2, = ax2.plot(faxis, 10 * np.log10(fft.fftshift(spectrum2+1)), '-')
    ax2.set_xlabel('Frequency (MHz)')
    ax2.set_ylabel('Power (dB arb.)')
    ax2.set_title('USB')
    
    # ax2.axvline((3-1.10712)*1000, color = "red")
    ax2.set_ylim([0, 150])  

    # line3, = ax3.plot(faxis, np.abs(10 * np.log10(fft.fftshift(spectrum1+1)/fft.fftshift(spectrum2+1))), '-')
    # ax3.set_xlabel('Frequency (MHz)')
    # ax3.set_ylabel('SRR (dB)')
    # ax3.set_title('Sideband Rejection Ratio')
    
    # # ax3.axvline((3-1.10712)*1000, color = "red")
    # ax3.set_ylim([-10, 100])  
    
    def update(frame, *fargs):

        spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)
        line1.set_ydata(10 * np.log10(fft.fftshift(spectrum1+1)))
        line2.set_ydata(10 * np.log10(fft.fftshift(spectrum2+1)))
        # line3.set_ydata(np.abs(10 * np.log10(fft.fftshift(spectrum1+1)/fft.fftshift(spectrum2+1))))

    v = anim.FuncAnimation(fig, update, frames=1, repeat=True, fargs=None, interval=10)
    plt.tight_layout() 
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Shows real time sidebands spectrums and SRR with given options',
        usage='python anim_dss_spectrum_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <Data Output Width>[options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Operation mode: Nfft Size')
    parser.add_argument('n_bits', type=int, help='BRAMs data output width')

    parser.add_argument('-l', '--acc_len', type=int, default=2**9,
                        help='Set the number of vectors to accumulate between dumps. Default is 2*(2^28)/2048')
    parser.add_argument('-s', '--skip', action='store_true',
                        help='Skip programming and begin to plot data')
    parser.add_argument('-b', '--fpgfile', type=str, default='',
                        help='Specify the FPG file to load')

    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft
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

    try:
        plot_spectrum(fpga, Nfft, n_bits)
    except KeyboardInterrupt:
        sys.exit()
