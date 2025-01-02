import casperfpga
import time

'''The next code is intended to test the Reset signal on the RFSoC board.
This signal prepares the spectrometer for every cycle of integration and resets
the counter of accumulation in every falling edge.'''

fpga = casperfpga.CasperFpga('10.17.90.40')     # Use your RFSoC IP address
print('Done')

fpga.upload_to_ram_and_program('8192ch_32bits_reset/dss_ideal_8192ch_32bits_reset_1966mhz_cx.fpg')

print('Configuring accumulation period...')
fpga.write_int('acc_len', 2**13)
# fpga.write_int('acc_len_pic', 2**12)
time.sleep(1)
print('Done')

print('Resetting counters...')
time.sleep(1)
fpga.write_int('cnt_rst', 1)
time.sleep(1)
fpga.write_int('cnt_rst', 0)
time.sleep(1)
print('Done')

"""The next while cycle print the time when the software register block 'acc_per_cycle'
reads 0, which means that the accumulation counter on the spectrometer was reset."""
t = time.time()
while True:
    # time.sleep(1)
    # print(f"sync_cnt:{fpga.read_uint('sync_cnt')}")
    print(f"acc_per_cycle:{fpga.read_uint('acc_per_cycle')}")
    # print(f"acc_cnt:{fpga.read_uint('acc_cnt')}")
    if fpga.read_uint('acc_per_cycle') == 0:
        print(round(time.time()-t, 5))

