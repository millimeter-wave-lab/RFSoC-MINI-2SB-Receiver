import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import casperfpga
import pyvisa
import argparse
import csv

def get_vacc_data_re_im(fpga, n_outputs, nfft):
  """Get the raw data from fpga digital correlator"""

  bins_out = nfft//n_outputs    # Number of bins for each output
    
  data_width = 8    # 8 bytes (64 bits)

  data_type = 'q'   # Format character 'long long'

  add_width = bins_out    # Number of "Data Width" words of the implemented BRAM
                          # Must be set to store at least the number of output bins of each bram

  raw1 = np.zeros((n_outputs, bins_out))
  raw2 = np.zeros((n_outputs, bins_out))
    
  for i in range(n_outputs):    # Extract data from BRAMs blocks for each output
    
    raw1[i,:] = struct.unpack(f'>{bins_out}{data_type}',
    fpga.read(f'ab_re{i}', add_width * data_width, 0))
    raw2[i,:] = struct.unpack(f'>{bins_out}{data_type}',
    fpga.read(f'ab_im{i}', add_width * data_width, 0))

  re = raw1.T.ravel().astype(np.float64)
  im = raw2.T.ravel().astype(np.float64)

  return re, im

def plot_phase_diff(fpga, instrument, Nfft, bin_step, output_file='phase_diff_data.csv'):
    '''Sweeps frequencies and plots phase difference with given options'''

    fs = 3932.16/2      # Bandwidth
    LO = 3000       # Local Oscillator
    phase = []      # Phase Difference
    freq_data = []
    
    try:
        n_outputs = 8
        if_freqs = np.linspace(0, fs, Nfft, endpoint=False)
        faxis_LSB = LO - if_freqs
        faxis_USB = LO + if_freqs

        for i in range(0, Nfft, bin_step):
            instrument.write(f'FREQ {faxis_LSB[-i-1]}e6')
            time.sleep(0.1)

            re, im = get_vacc_data_re_im(fpga, n_outputs=n_outputs, nfft=Nfft)
            comp = fft.fftshift(re + 1j*im)
            angle = np.angle(comp[-1-i], deg=True)
            
            freq_data.append(faxis_LSB[-i-1] / 1000)
            phase.append(angle)
            print(faxis_LSB[-i-1]/1000, angle)

        for i in range(0, Nfft, bin_step):
            instrument.write(f'FREQ {faxis_USB[i]}e6')
            time.sleep(0.1)

            re, im = get_vacc_data_re_im(fpga, n_outputs=n_outputs, nfft=Nfft)
            comp = fft.fftshift(re + 1j*im)
            angle = np.angle(comp[i], deg=True)
            
            freq_data.append(faxis_USB[i] / 1000)
            phase.append(angle)
            print(faxis_USB[i]/1000, angle)
    
    except KeyboardInterrupt:
        print("User interruption. Plotting data...")

    # Save CSV
    with open(output_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Frequency (MHz)", "Phase Difference (degrees)"])
        csv_writer.writerows(zip(freq_data, phase))

    faxis = np.concatenate((faxis_LSB[::-1][::bin_step], faxis_USB[::bin_step]))[:len(phase)]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.grid()
    ax.plot(faxis, phase, '-', color="black")
    
    ax.set_xlabel('RF Frequency (MHz)')
    ax.set_ylabel('Phase Difference in Degrees')
    ax.set_title('Measured Phase Difference between IF Outputs')
    ax.set_ylim(-180, 180)

    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Sweeps frequencies and plots phase difference with given options',
        usage='python sweep_ph_plot_1966mhz.py <HOSTNAME_or_IP> <Nfft Size> <RF instrument IP address>'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Nfft Size')
    parser.add_argument('rf_instrument', type=str, help='RF instrument IP address')
    parser.add_argument('-l', '--acc_len', type=int, default=2**13,
                        help='Set the number of vectors to accumulate between dumps.')

    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft
    rf_instrument = args.rf_instrument
    
    # Use your .fpg file
    bitstream = '/home/jose/Workspace/rfsoc_models/DSS/dss_ideal_16384ch_1966mhz_cx/outputs/dss_ideal_16384ch_1966mhz_cx_2024-10-24_1244.fpg'

    print(f'Connecting to {hostname}...')
    fpga = casperfpga.CasperFpga(hostname)
    time.sleep(1)

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
        plot_phase_diff(fpga, instrument, Nfft, 1)
    except KeyboardInterrupt:
        sys.exit()