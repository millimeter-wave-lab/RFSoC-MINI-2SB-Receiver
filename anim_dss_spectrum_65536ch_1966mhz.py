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

  data_width = 4    # 4 bytes (32 bits)

  data_type = 'L'   # Format character 'unsigned long'
  
  if nfft == 512:
     
     bram_name = 're_bin_synth'

  else:
     bram_name = 'synth'

  add_width = bins_out    # Number of "Data Width" words of the implemented BRAM
                          # Must be set to store at least the number of output bins of each bram

  raw1 = np.zeros((n_outputs, bins_out))
  raw2 = np.zeros((n_outputs, bins_out))
  
  for i in range(n_outputs):    # Extract data from BRAMs blocks for each output
    
    raw1[i,:] = struct.unpack(f'>{bins_out}{data_type}',
    fpga.read(f'{bram_name}0_{i}', add_width * data_width, 0))

    raw2[i,:] = struct.unpack(f'>{bins_out}{data_type}',
    fpga.read(f'{bram_name}1_{i}', add_width * data_width, 0))
    
  interleave_i = raw1.T.ravel().astype(np.float64) 
  interleave_q = raw2.T.ravel().astype(np.float64)

  return interleave_i, interleave_q

def plot_spectrum(fpga, Nfft, n_bits, n):
    
    fig, (ax1, ax2) = plt.subplots(1, 2) 
    ax1.grid()
    ax2.grid()

    print(Nfft)

    fs = 3932.16 / 2
    n_outputs = 8
       
    spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)

    if n == 1:
       faxis = np.linspace(0,fs/2, Nfft ,endpoint=False)
       LSB = 10 * np.log10(fft.fftshift(spectrum2+1))
       USB = 10 * np.log10(fft.fftshift(spectrum1+1))

    else:
       faxis = np.linspace(fs/2,fs, Nfft ,endpoint=False)[1:]
       LSB = 10 * np.log10(fft.fftshift(spectrum2+1))[:-1]
       USB = 10 * np.log10(fft.fftshift(spectrum2+1))[:-1]

    line1, = ax1.plot(faxis, LSB, '-')
    ax1.set_xlabel('Frequency (MHz)')
    ax1.set_ylabel('Power (dB arb.)')
    ax1.set_title('LSB')

    # ax1.axvline(1474.56, color = "red")
    # ax1.set_xlim([1474.47, 1474.65]) 
    ax1.set_ylim([0, 160]) 

    line2, = ax2.plot(faxis, USB, '-')
    ax2.set_xlabel('Frequency (MHz)')
    ax2.set_ylabel('Power (dB arb.)')
    ax2.set_title('USB')
    
    # ax2.axvline(1474.56, color = "red")
    # ax2.set_xlim([1474.47, 1474.65])
    ax2.set_ylim([0, 160])

    if n == 1:
       
        def update(frame, *fargs):

            spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)
            line1.set_ydata(10 * np.log10(fft.fftshift(spectrum2+1)))
            line2.set_ydata(10 * np.log10(fft.fftshift(spectrum1+1)))

    else:
       
        def update(frame, *fargs):

            spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)
            line1.set_ydata(10 * np.log10(fft.fftshift(spectrum2+1))[:-1])
            line2.set_ydata(10 * np.log10(fft.fftshift(spectrum1+1))[:-1])
    
    v = anim.FuncAnimation(fig, update, frames=1, repeat=True, fargs=None, interval=10)
    plt.tight_layout() 
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Shows real time sidebands spectrums and SRR with given options',
        usage='python anim_dss_spectrum_65536ch_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <Data Output Width> <part>[options]'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Operation mode: Nfft Size')
    parser.add_argument('data_output_width', type=int, help='BRAMs data output width')
    parser.add_argument('spectrum_part', type=int, help='For the 65536-size FFT models, select either the first or second half of the bandwidth')
    
    parser.add_argument('-l', '--acc_len', type=int, default=2**13,
                        help='Set the number of vectors to accumulate between dumps. Default is 2*(2^28)/2048')
    
    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft
    n_bits = args.data_output_width
    part = args.spectrum_part

    # Use your .fpg file
    bitstream = f'/home/jose/Workspace/RFSoC-MINI-2SB-Receiver/32_bits_models/65536ch_32bits_reset/dss_ideal{part}_65536ch_32bits_reset_1966mhz_cx.fpg'
    
    print(f'Connecting to {hostname}...')
    fpga = casperfpga.CasperFpga(hostname)
    time.sleep(0.2)

    print(f'Programming FPGA with {bitstream}...')
    fpga.upload_to_ram_and_program(bitstream)
    print('Done')

    print('Initializing RFDC block...')
    fpga.adcs['rfdc'].init()
    c = fpga.adcs['rfdc'].show_clk_files()
    fpga.adcs['rfdc'].progpll('lmk', c[1])
    fpga.adcs['rfdc'].progpll('lmx', c[0])
    time.sleep(1)

    print('Configuring accumulation period...')
    fpga.write_int('acc_len', args.acc_len)
    time.sleep(0.2)
    fpga.write_int('acc_len_re_bin', args.acc_len)
    time.sleep(0.2)

    if n_bits == 32:
       fpga.write_int('gain', 2**20)
       fpga.write_int('gain_re_bin', 2**20)
    time.sleep(1)
    print('Done')

    print('Resetting counters...')
    fpga.write_int('cnt_rst', 1)
    fpga.write_int('cnt_rst', 0)
    time.sleep(1)
    print('Done')

    try:
        plot_spectrum(fpga, Nfft, n_bits, part)
    except KeyboardInterrupt:
        sys.exit()