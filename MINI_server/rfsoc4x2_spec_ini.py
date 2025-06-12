# Initialization script 
import sys, time, struct
import numpy as np
from numpy import fft
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import casperfpga

hostname='10.17.90.187'
# Use your .fpg file    
bitstream = '/home/jose/Workspace/RFSoC-MINI-2SB-Receiver/8192ch_32bits_reset/dss_ideal_8192ch_32bits_reset_1966mhz_cx/outputs/dss_ideal_8192ch_32bits_reset_1966mhz_cx_2025-04-07_1901.fpg'

n_bits = 32
print(f'Connecting to {hostname}...')
fpga = casperfpga.CasperFpga(hostname)
time.sleep(0.2)

fpga.upload_to_ram_and_program(bitstream)

print('Initializing RFDC block...')
fpga.adcs['rfdc'].init()
c = fpga.adcs['rfdc'].show_clk_files()
fpga.adcs['rfdc'].progpll('lmk', c[1])
fpga.adcs['rfdc'].progpll('lmx', c[0])
time.sleep(1)

print('Configuring accumulation period...')
fpga.write_int('acc_len', 2**13)
fpga.write_int('acc_len_re_bin', 2**13)
fpga.write_int('gain', 2**20)
fpga.write_int('gain_re_bin', 2**20)
time.sleep(1)
print('Done')

print('Resetting counters...')
fpga.write_int('cnt_rst', 1)
fpga.write_int('cnt_rst', 0)
time.sleep(1)
print('Done')