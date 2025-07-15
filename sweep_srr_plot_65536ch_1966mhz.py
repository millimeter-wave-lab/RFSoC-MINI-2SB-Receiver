import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import casperfpga
import pyvisa
import time
import argparse
import csv

def get_vacc_data_power(fpga, n_outputs, nfft, n_bits):
  """Get the raw data from fpga digital sideband separation spectrometer"""

  bins_out = nfft//n_outputs    # Number of bins for each output

  if n_bits == 64:    # Shared BRAMs data width of 8 bytes (64 bits)
    
    data_width = 8    # 8 bytes (64 bits)

    data_type = 'Q'   # Format character 'unsigned long long'
  
  else:               # Shared BRAMs data width of 4 bytes (32 bits)
    
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

def sweep_SRR(fpga, instrument, Nfft, n_bits, bin_step, n, output_file='srr_data.csv'):
    '''Sweeps frequencies and plots SRR with given options, and saves data to CSV.'''
    
    fs = 3932.16 / 2  # Bandwidth
    LO = 3000  # Local Oscillator
    SRR = []  # Sideband Rejection Ratio
    freq_data = []

    try:
        n_outputs = 8
        
        if n == 1:
            if_freqs = np.linspace(0, fs/2, Nfft, endpoint=False)
            faxis_LSB = LO - if_freqs
            faxis_USB = LO + if_freqs

            for i in range(0, Nfft, bin_step):
                instrument.write(f'FREQ {faxis_LSB[-i-1]}e6')
                time.sleep(0.5)
                
                spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)

                diff = 10 * (np.log10(fft.fftshift(spectrum2 + 1)[-i-1] / fft.fftshift(spectrum1 + 1)[-i-1]))
                
                print(faxis_LSB[-i-1] / 1000, diff)
                freq_data.append(faxis_LSB[-i-1] / 1000)
                SRR.append(diff)

            for i in range(0, Nfft, bin_step):
                instrument.write(f'FREQ {faxis_USB[i]}e6')
                time.sleep(0.5)
                
                spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)

                diff = 10 * (np.log10(fft.fftshift(spectrum1 + 1)[i] / fft.fftshift(spectrum2 + 1)[i]))
                
                print(faxis_USB[i] / 1000, diff)
                freq_data.append(faxis_USB[i] / 1000)
                SRR.append(diff)

        else:
            
            """First frequency on 'if_freqs' discarded (983.04 MHz).
            Now starts on 983.07 MHz and ends on 1966.05 MHz.
            Channels read by RFSoC adjusted to match with array dimensions 
            and frequencies with 'if_freqs'."""
            if_freqs = np.linspace(fs/2, fs, Nfft, endpoint=False)[1:]
            faxis_LSB = LO - if_freqs
            faxis_USB = LO + if_freqs

            for i in range(0, Nfft-1, bin_step):
                instrument.write(f'FREQ {faxis_LSB[-i-1]}e6')
                time.sleep(0.5)
                
                spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)

                diff = 10 * (np.log10(fft.fftshift(spectrum2 + 1)[-i-2] / fft.fftshift(spectrum1 + 1)[-i-2]))
                
                print(faxis_LSB[-i-1] / 1000, diff)
                freq_data.append(faxis_LSB[-i-1] / 1000)
                SRR.append(diff)

            for i in range(0, Nfft-1, bin_step):
                instrument.write(f'FREQ {faxis_USB[i]}e6')
                time.sleep(0.5)
                
                spectrum1, spectrum2 = get_vacc_data_power(fpga, n_outputs=n_outputs, nfft=Nfft, n_bits=n_bits)

                diff = 10 * (np.log10(fft.fftshift(spectrum1 + 1)[i] / fft.fftshift(spectrum2 + 1)[i]))
                
                print(faxis_USB[i] / 1000, diff)
                freq_data.append(faxis_USB[i] / 1000)
                SRR.append(diff)

    except KeyboardInterrupt:
        print("User interruption. Plotting data...")
    
    # Save CSV
    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Frequency (MHz)", "SRR (dB)"])
        csv_writer.writerows(zip(freq_data, SRR))

    if_freqs = np.concatenate((faxis_LSB[::-1][::bin_step], faxis_USB[::bin_step]))[:len(SRR)]
    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.grid()
    ax.plot(if_freqs, SRR, '-', color="black")
    
    plt.xlabel('RF Frequency (MHz)')
    plt.ylabel('SRR (dB)')
    plt.title('Sideband Rejection Ratio')
    ax.set_ylim(-10, 70)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Sweeps frequencies and plots SRR with given options',
        usage='python sweep_srr_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF Instrument IP address> <Data Output Width>'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Nfft Size')
    parser.add_argument('rf_instrument', type=str, help='RF instrument IP address')
    parser.add_argument('data_output_width', type=int, help='BRAMs data output width')
    parser.add_argument('spectrum_part', type=int, help='For the 65536-size FFT models, select either the first or second half of the bandwidth')

    parser.add_argument('-l', '--acc_len', type=int, default=2**13,
                        help='Set the number of vectors to accumulate between dumps')

    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft
    rf_instrument = args.rf_instrument
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
    print('Done')
    # time.sleep(25)

    print('Configuring accumulation period...')
    fpga.write_int('acc_len', args.acc_len)
    time.sleep(0.2)
    fpga.write_int('acc_len_re_bin', args.acc_len)
    time.sleep(0.2)
    
    if n_bits == 32:
       fpga.write_int('gain', 2**20)
       fpga.write_int('gain_re_bin', (2**20)//(Nfft//512))
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
        sweep_SRR(fpga, instrument, Nfft, n_bits, 128, part)
    except KeyboardInterrupt:
        sys.exit()
