import sys, time, struct
import numpy as np
import casperfpga
import argparse

def float2fixed(data, nbits, binpt, signed=True):
    """
    Convert an array of floating points to fixed points, with width number of
    bits nbits, and binary point binpt. Optional warinings can be printed
    to check for overflow in conversion.
    :param data: data to convert.
    :param nbits: number of bits of the fixed point format.
    :param binpt: binary point of the fixed point format.
    :param signed: if true use signed representation, else use unsigned.
    :return: data in fixed point format.

    This function was developed by Franco Curotto in July 2024.
    """

    nbytes = int(np.ceil(nbits/8))
    dtype = '>i'+str(nbytes) if signed else '>u'+str(nbytes)

    fixedpoint_data = (2**binpt * data).astype(dtype)
    return fixedpoint_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Loads complex constants into BRAMs of a CASPER-based system.',
        usage='python load_conts.py <HOSTNAME_or_IP> <Nfft Size> <Cal_State>'
    )

    parser.add_argument('hostname', type=str, help='Hostname or IP for the Casper platform')
    parser.add_argument('nfft', type=int, help='Nfft Size')
    parser.add_argument('cal_state', type=int, choices=[0, 1], help='Calibration state: 0 for uncalibrated system, 1 for calibrated system')

    args = parser.parse_args()

    hostname = args.hostname
    Nfft = args.nfft
    cal_state = args.cal_state

    print(f'Connecting to {hostname}...')
    fpga = casperfpga.CasperFpga(hostname)
    time.sleep(0.2)

    if cal_state == 0:    # Case 1: Uncalibrated, ideal calibration constants used (0 + 1j)
        
        print('Writing Ideal Calibration Constants (0 + 1j)')

        # Loop over BRAM blocks to load complex calibration constants
        # Each BRAM will be filled with a fixed-point representation of 0s and 1s
        # This represents real components = 0.0 and imaginary components = 1.0
        for i in range(8):
            
            # Write 0 in fixed-point representation
            fpga.write(f"bram_mult0_{i}_bram_re", 
                       float2fixed(np.zeros(Nfft//8), 32, 30).tobytes(), 
                       0)
            
            fpga.write(f"bram_mult1_{i}_bram_re", 
                       float2fixed(np.zeros(Nfft//8), 32, 30).tobytes(), 
                       0)

            # Write 1 in fixed-point representation
            fpga.write(f"bram_mult0_{i}_bram_im", 
                       float2fixed(np.ones(Nfft//8), 32, 30).tobytes(), 
                       0)
            
            fpga.write(f"bram_mult1_{i}_bram_im", 
                       float2fixed(np.ones(Nfft//8), 32, 30).tobytes(), 
                       0)

    else:       # Case 2: Calibrated, load calibration constants previously calculated

        # # Generate the array of Nfft complex values: 0 + 1j
        # const_array = np.full(Nfft, 0 + 1j, dtype=np.complex64)

        # # Save to file in binary format (.npy)
        # np.save('complex_constants.npy', const_array)

        # print("Array saved to 'complex_constants.npy'")

        print("Loading calibration constants")

        # Load the .npy file with calibration constants
        const_array_0 = np.load('complex_constants.npy')
        const_array_1 = np.load('complex_constants.npy')

        # Reorder data with calibration constants to write BRAMs
        deinterleaved_const_0 = np.transpose(np.reshape(const_array_0, (Nfft//8, 8)))
        deinterleaved_const_1 = np.transpose(np.reshape(const_array_1, (Nfft//8, 8)))
        
        print('Writing Calibration Constants')

        # Loop over BRAM blocks to load complex calibration constants
        for i in range(8):
            
            # Write real component in fixed-point representation
            fpga.write(f"bram_mult0_{i}_bram_re", 
                       float2fixed(np.real(deinterleaved_const_0[i]), 32, 30).tobytes(), 
                       0)
            
            fpga.write(f"bram_mult1_{i}_bram_re", 
                       float2fixed(np.real(deinterleaved_const_1[i]), 32, 30).tobytes(), 
                       0)

            # Write imaginary component in fixed-point representation
            fpga.write(f"bram_mult0_{i}_bram_im", 
                       float2fixed(np.imag(deinterleaved_const_0[i]), 32, 30).tobytes(), 
                       0)
            
            fpga.write(f"bram_mult1_{i}_bram_im", 
                       float2fixed(np.imag(deinterleaved_const_1[i]), 32, 30).tobytes(), 
                       0)

    print('Done')
