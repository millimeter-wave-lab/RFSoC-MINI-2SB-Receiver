#!/usr/bin/env python3

# SOCKET SERVER

import socket
import struct
import time, datetime

import threading
import queue
import select
import numpy as np
import casperfpga
from numpy import fft
import csv

import os
import cpp_socket

# Define IP and port to use

# REMEMBER TO SET COMPUTER's IP TO 192.168.1.14

HOST_PIC = "192.168.7.119" # IP
PORT_PIC = 1234 # Port to listen on

# Define the numbers of telescope states per package, and the packet length
statesPerPackage = 20
packetLength = 70

# Events for sockets
#receivingFromPIC = threading.Event()
#sendingToPIC = threading.Event()
#receivingFromROACH = threading.Event()
#sendingToROACH = threading.Event()

# Queue for sending
RFSoC_requests_queue = queue.Queue()
send_to_PIC_queue = queue.Queue()
spectra_write_to_disk_queue = queue.Queue()



# def isTelescopeStatus(data):
# 	"""
#     Checks if the data received is the telescope status, return 1 if it is,
#     and returns 0 if otherwise.
#     data:	Data received from the PIC
#     """
# 	if data[0:2].decode('ascii') == "ST":
# 		#print(data)
# 		return 1
# 	else:
# 		return 0

# Read and change to target path for storing the data
with open('datapath.txt') as f:
    lines = f.readlines()

target_path = lines[0][:lines[0].index('\n')]
os.chdir(target_path)
  
# checking if the data directory
# exists or not
if not os.path.exists("bin_spectra_and_states"):
      
    # if the directory is not present 
    # then create it.
    os.makedirs("bin_spectra_and_states")

def program_fpga(fpga):
	"""
	Function to program the fpga
	"""
	a = 0
	# Program fpga and stuff
def request_acc_cnt(client):
	acc_recv = client.send_request('acc_cnt 0 4', 4)
	# acc_recv = client.send_request('acc_cnt 0 4')
	#print(f"acc_recv: {acc_recv}")
	acc_int = struct.unpack('<1L', acc_recv)[0]
	#print(f"acc_int: {acc_int}")
	acc_cnt_hex = hex(acc_int)
	# 4 Bytes!!! Will this be a problem? Maybe PIC reads only 2 bytes
	#acc_cnt_hex = hex(acc_cnt)

	acc_bytes = str.encode(acc_cnt_hex)
	#response = acc_cnt.to_bytes(2, byteorder = "big")
	return acc_bytes


def request_channels(client, first_chan: int, Nfft: int, N_Channels: int, mode: str):
    
	"""Get the raw data in bytes from fpga digital spectrometer from requested channels using a client interface.

    :param client: object used to communicate with RFSoC.
    :param first_chan: index of the first FFT channel to request (starting from 0).
    :param Nfft: total number of FFT bins.
    :param N_Channels: number of frequency channels to receive.
    :param mode: observation mode, i.e. 'cal' or 'splobs'.
    
	:return: byte array containing the requested data.
    """
	n_outputs = 8
	
	bins_out = N_Channels // 8
	bram_name = "synth"

	if mode == 'cal':
		first_chan = 0
		# EN CASO DE QUERER CALIBRAR CON UNA SECCIÓN DEL ESPECTRO COMPLETO: Cambiar first_chan al que nos interesa 
		
		Nfft = 512
		# Cambiar Nfft al de interés (igual que se ingresa al inicio de request_channel, p.ej 8192)
		
		N_Channels = Nfft
		# Cambiar N_Channels a 512 para que le llegue bien a la PIC

		bins_out = N_Channels // 8
		bram_name = "re_bin_synth"
		# bram_name Cambiar a "synth" para usar el espectrómetro original

	data_width = 4    # Data output width of 4 bytes (32 bits)
	add_width = bins_out    # Number of "Data Width" words of the implemented BRAM
							# Must be set to store at least the number of output bins of each bram

	# print("")
	raw1 = np.zeros((n_outputs, bins_out))
	raw2 = np.zeros((n_outputs, bins_out))

	# Case 1: first_chan//8 <= (Nfft//8)//2
	if first_chan//8 <= (Nfft//8)//2:
		
		# Case 1.1: (Nfft//8)//2 + first_chan//8 + N_Channels//8 <= Nfft//8
		if (Nfft//8)//2 + first_chan//8 + N_Channels//8 <= Nfft//8:
			for i in range(n_outputs):	# Extract data from BRAMs blocks for each output
				
				data_in_bytes_USB = client.send_request(f"{bram_name}0_{i} {((Nfft//8)//2 + first_chan//8) * data_width} {add_width * data_width}", add_width * data_width)
				# print(f"Requested bytes {add_width * data_width}")
				# print(f"USB {len(data_in_bytes_USB)}")
				
				raw1[i,:] = struct.unpack(f'<{bins_out}L', data_in_bytes_USB)
				time.sleep(0.0005)
				
				data_in_bytes_LSB = client.send_request(f"{bram_name}1_{i} {((Nfft//8)//2 + first_chan//8) * data_width} {add_width * data_width}", add_width * data_width)
				raw2[i,:] = struct.unpack(f'<{bins_out}L', data_in_bytes_LSB)
				time.sleep(0.0005)

		else:
			first_half = (Nfft//8)//2 - first_chan//8
			second_half = first_chan//8 + N_Channels//8 - (Nfft//8)//2
			
			for i in range(n_outputs):

				data_in_bytes_USB_1 = client.send_request(f"{bram_name}0_{i} {((Nfft//8)//2 + first_chan//8) * data_width} {first_half * data_width}", first_half * data_width)
				data_in_bytes_USB_2 = client.send_request(f"{bram_name}0_{i} {0} {second_half * data_width}", second_half * data_width)
				# print(f"Requested First bytes {first_half * data_width}")
				# print(f"Requested Second bytes {second_half * data_width}")
				# print(f"USB 1 {len(data_in_bytes_USB_1)}")
				# print(f"USB 2 {len(data_in_bytes_USB_2)}")
				raw1[i,:] = struct.unpack(f'<{bins_out}L', data_in_bytes_USB_1 + data_in_bytes_USB_2)
				time.sleep(0.0005)

				data_in_bytes_LSB_1 = client.send_request(f"{bram_name}1_{i} {((Nfft//8)//2 + first_chan//8) * data_width} {first_half * data_width}", first_half * data_width)
				data_in_bytes_LSB_2 = client.send_request(f"{bram_name}1_{i} {0} {second_half * data_width}", second_half * data_width)
				raw2[i,:] = struct.unpack(f'<{bins_out}L', data_in_bytes_LSB_1 + data_in_bytes_LSB_2)
				time.sleep(0.0005)

	# Case 2: first_chan//8 > (Nfft//8)//2
	else:
			for i in range(n_outputs):	# Extract data from BRAMs blocks for each output
				data_in_bytes_USB = client.send_request(f"{bram_name}0_{i} {(first_chan//8 - (Nfft//8)//2) * data_width} {add_width * data_width}", add_width * data_width)
				raw1[i,:] = struct.unpack(f'<{bins_out}L', data_in_bytes_USB)
				time.sleep(0.0005)
				
				data_in_bytes_LSB = client.send_request(f"{bram_name}1_{i} {(first_chan//8 - (Nfft//8)//2) * data_width} {add_width * data_width}", add_width * data_width)
				raw2[i,:] = struct.unpack(f'<{bins_out}L', data_in_bytes_LSB)
				time.sleep(0.0005)
	
	
	interleave_USB = raw1.T.ravel().astype(np.uint32) 
	interleave_LSB = raw2.T.ravel().astype(np.uint32)

	return [interleave_USB, interleave_LSB]

# def request_512_channels_and_save(fpga):
# 	"""Get the raw data in bytes from fpga digital spectrometer"""
# 	n_outputs = 8
# 	nfft = 8192
# 	N_CHANNELS = 512 # Number of channels to read
# 	FIRST_CHANNEL = 768 # the first channel to read, copied from Roach communication
# 	#q, i = get_vacc_data_power(fpga, n_outputs, nfft)

# 	spectra_write_to_disk_queue.put([q, i])

# 	spectrum_for_pic = q[FIRST_CHANNEL:FIRST_CHANNEL+N_CHANNELS]
# 	return spectrum_for_pic

# 	# Pack the first 512 values

def set_cal_mode(fpga):
	#fpga.write_int('acc_len', ACC_LEN_CAL)
	acc_len = fpga.read_uint('acc_len')
	print("FPGA acc len set to " + str(acc_len))
	print("CAL Mode")
	return "cal"

def set_splobs_mode(fpga):
	#fpga.write_int('acc_len', ACC_LEN_SPLOBS)
	acc_len = fpga.read_uint('acc_len')
	print("FPGA acc len set to " + str(acc_len))
	print("SPLOBS Mode")
	# return "cal"
	return "splobs"

def receive_from_PIC(PIC_socket):
	"""
	Receives the data from the PIC socket and if it is the telescope status,
	saves it into a binary file.
	PIC_socket:	PIC socket
	"""

	# Initializes filename of the csv to save, and the folder of states
	filename = "bin_spectra_and_states/"+str(datetime.datetime.now())+"_STATE"
	filename = filename.replace(" ", "_")

	with open(filename, 'ab') as f:
		while True:
			try:
				while True:
					rlist, _, _ = select.select([PIC_socket], [], [])
					#if not sendingToPIC.is_set():
					#receivingFromPIC.set()
					#print("Receiving from PIC:")
					data_from_PIC = PIC_socket.recv(2048)
					
					while True:
						statusIndex = data_from_PIC.find(b'ST')
						if statusIndex != -1:
							# Data containing status from the telescope, saving to server

							f.write(data_from_PIC[statusIndex:statusIndex+packetLength])
							#print(dataFromPIC[statusIndex:statusIndex+packetLength])
							#print("Saving telescope status at:")
							#print(time.time())
							data_from_PIC = data_from_PIC[:statusIndex] + data_from_PIC[statusIndex+packetLength:]
						else:
							break

					if len(data_from_PIC) != 0:
						# Data going to RFSoC
						#print("PIC: ",data_from_PIC)
						RFSoC_requests_queue.put(data_from_PIC)
							

						#send_to_RFSOC_queue.put(dataFromPIC)

					#print("Received from PIC and added to queue:")
					#print(dataFromPIC)
					#if isTelescopeStatus(dataFromPIC):
					#	f.write(dataFromPIC[:])
					#	print("Saving telescope status at:")
					#	print(time.time())
					#else:
					#	PIC_queue.put(dataFromPIC)
					#receivingFromPIC.clear()
			finally:
				f.close()



def process_RFSoC_request(fpga, client, Nfft, N_CHANNELS):
	"""
	Receives the data from the RFSoC socket
	RFSoC_socket:	Rfsoc socket
	"""
	# Spectrum 512 ch buffer
	spectrum_buffer_512 = np.zeros(512).astype(np.uint32)
	last_acc = request_acc_cnt(client)
	counter = 0
	while True:
		request = RFSoC_requests_queue.get()
		if request[:17] == b"?wordread acc_cnt":
			counter += 1
			cnt_in_bytes = request_acc_cnt(client)
			response = b"!wordread ok "+ cnt_in_bytes+ b"\n"
			if cnt_in_bytes != last_acc:
				counter = 0
				#spectrum_buffer_512 = request_512_channels_and_save(fpga)
				#t1 = time.time()
				#spectrum_buffer_512 = request_512_channels(fpga)

				USB, LSB = request_channels(client, 0, Nfft, N_CHANNELS, mode)
				
				spectrum_buffer_512 = USB[:512]

				"""request_512_channels_1band(client, first_chan:int, Nfft:int, N_Channels: int, mode:str)"""
				
				#print(time.time()-t1)
				last_acc = cnt_in_bytes
			send_to_PIC_queue.put(response)
			#cnt_in_bytes = request_acc_cnt(fpga)
			#response_in_bytearray = bytearray(b"!read ok ")
			#response_in_bytearray.append(cnt_in_bytes)
			#bytes_result = bytes([byte for byte in response_in_bytearray])
			#send_to_PIC_queue.put(bytes_result)

		elif request[:11] == b"?read bram0":
			spectrum = spectrum_buffer_512
			spec_in_bytes = struct.pack(f">{len(spectrum)}L", *spectrum)
			response = b"!read ok " + spec_in_bytes + b"\n"
			send_to_PIC_queue.put(response)

			#spec_in_bytes = request_512_channels(fpga)
			#response_in_bytearray = bytearray(b"!read ok ")
			#response_in_bytearray.append(spec_in_bytes)
			#response_in_bytearray.append(b'\n')
			#bytes_result = bytes([byte for byte in response_in_bytearray])
			#send_to_PIC_queue.put(bytes_result)
			#spectra_write_to_disk_queue.put(spec_in_bytes)
			#save_full_spectrum(fpga)

		elif request[:8] == b"?progdev":
			response = b"!progdev ok 525\n"
			send_to_PIC_queue.put(response)
			#response_in_bytearray = bytearray(b"!progdev ok 525\n")
			#bytes_result = bytes([byte for byte in response_in_bytearray])
			#send_to_PIC_queue.put(bytes_result)

		elif request[:25] == b"?wordwrite integ_mode 0 0":
			mode = set_cal_mode(fpga)
			response = b"!wordwrite ok\n"
			send_to_PIC_queue.put(response)

		elif request[:25] == b"?wordwrite integ_mode 0 1":
			mode = set_splobs_mode(fpga)
			response = b"!wordwrite ok\n"
			send_to_PIC_queue.put(response)

		elif request[:10] == b"?wordwrite":
			response = b"!wordwrite ok\n"
			send_to_PIC_queue.put(response)

			#response_in_bytearray = bytearray(b"!wordwrite ok\n")
			#bytes_result = bytes([byte for byte in response_in_bytearray])
			#send_to_PIC_queue.put(bytes_result)

		elif request[:6] == b"?write":
			response = b"!write ok\n"
			send_to_PIC_queue.put(response)

			#response_in_bytearray = bytearray(b"!write ok\n")
			#bytes_result = bytes([byte for byte in response_in_bytearray])
			#send_to_PIC_queue.put(bytes_result)

		


def save_spectra_to_hdd():
	"""
	Saves spectra from queue to hard drive
	"""
		# Initializes filename of the csv to save, and the folder of states
	filename = "bin_spectra_and_states/"+str(datetime.datetime.now()) +"_ROACHDATA.csv"
	filename = filename.replace(" ", "_")

	with open(filename, 'a') as f:
		try:
			while True:
				#if not sendingToROACH.is_set():		
				#receivingFromROACH.set()
				#print("Receiving from ROACH:")
				spectrum = spectra_write_to_disk_queue.get()
				#print("Received from ROACH and added to queue:")
				#print(dataFromROACH)
				
				#f.write('Tmst')
				actualTime = time.time()
				#print(actualTime)
				f.write(str(actualTime))
				f.write("\n")
				csv.writer(f,delimiter=",").writerows(spectrum)
				#receivingFromROACH.clear()
		finally:
			f.close()

def sending_data(PIC_socket:socket):
	"""
	Sends the data to the PIC socket
	"""
	while True:
		_, wlist, _ = select.select([], [PIC_socket], [])
		for readysocket in wlist:
			if readysocket is PIC_socket and not send_to_PIC_queue.empty(): # and not receivingFromPIC.is_set():
				#sendingToPIC.set()
				data_to_PIC = send_to_PIC_queue.get()
				#print("DATASERVER: ",data_to_PIC)
				#print("Sending to PIC:")
				#print(dataToPIC)
				#print(len(dataToPIC))
				PIC_socket.send(data_to_PIC)
				#now = datetime.datetime.now()
				#print(now.time())
				#sendingToPIC.clear()

"""
MAIN PROGRAM
""" 

"""
ROACH_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print(f"Waiting for connection to {HOST_RF} Port {PORT_ROACH}")
ROACH_s.connect((HOST_ROACH, PORT_ROACH))
print(f"Connected to {HOST_ROACH}")

CONNECT TO RFSOC HERE!!!!!!!
"""
HOST_RFSOC = "192.168.7.187"
client = cpp_socket.CPPSocket(HOST_RFSOC, 12345)

# FPGA Model Parameters
NFFT = 8192		# FFT Size (2**14 = 16384)
N_CHANNELS = 8192	#Number of spectral channels to read (2**14 = 16384)

if NFFT == 8192:
	ACC_LEN_SPLOBS = 2**12
	ACC_LEN_CAL = 2**12

elif NFFT == 16384:
	ACC_LEN_SPLOBS = 2**11
	ACC_LEN_CAL = 2**11

elif NFFT == 32768:
	ACC_LEN_SPLOBS = 2**10
	ACC_LEN_CAL = 2**10

elif NFFT == 65536:
	ACC_LEN_SPLOBS = 2**9
	ACC_LEN_CAL = 2**9

GAIN_RE_BIN = 2**11
GAIN = GAIN_RE_BIN * NFFT // 512

print(f'NFFT 1 = {NFFT}')
print(f'Gain 1 = {GAIN}')

hostname = HOST_RFSOC	# IP address RFSoC

# FPGA .fpg file and .dtbo must be in the same folder

bitstream = f'/home/mini-dataserver/miniQuimal/src/dataserver_as_interface/models/dss_ideal_{NFFT}ch_32bits_reset_1966mhz_cx.fpg'

if NFFT == 65536:
	bitstream = f'/home/mini-dataserver/miniQuimal/src/dataserver_as_interface/models/dss_ideal1_{NFFT}ch_32bits_reset_1966mhz_cx.fpg'
	NFFT = NFFT//2


print(f'Connecting to {hostname}...')
fpga = casperfpga.CasperFpga(hostname)
time.sleep(0.2)

print(f'Programming FPGA with {bitstream}...')
fpga.upload_to_ram_and_program(bitstream)
time.sleep(1)
print('Done')

print('Initializing RFDC block...')    
fpga.adcs['rfdc'].init()
c = fpga.adcs['rfdc'].show_clk_files()
fpga.adcs['rfdc'].progpll('lmk', c[1])
fpga.adcs['rfdc'].progpll('lmx', c[0])
time.sleep(1)

print('Configuring accumulation period...')

fpga.write_int('acc_len', ACC_LEN_SPLOBS)
fpga.write_int('acc_len_re_bin', ACC_LEN_SPLOBS)
fpga.write_int('gain', GAIN)
fpga.write_int('gain_re_bin', GAIN_RE_BIN)

time.sleep(1)

print('Done')

print('Resetting counters...')
fpga.write_int('cnt_rst', 1)
fpga.write_int('cnt_rst', 0)
time.sleep(1)
print('Done')


#fpga = casperfpga.CasperFpga(HOST_RFSOC)

PIC_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
PIC_s.bind((HOST_PIC, PORT_PIC))
PIC_s.listen()
print(f"Waiting for connection in {HOST_PIC} Port {PORT_PIC}")
conn, addr = PIC_s.accept()
print(f"Connected to {addr}")


recv_from_PIC_thread = threading.Thread(target=receive_from_PIC,args=([conn]))
process_RFSoC_request_thread = threading.Thread(target=process_RFSoC_request, args=([fpga, client, NFFT, N_CHANNELS]))
#process_RFSoC_request_thread = threading.Thread(target=process_RFSoC_request)
sending_data_thread = threading.Thread(target=sending_data, args=([conn]))
saving_spectra_thread = threading.Thread(target=save_spectra_to_hdd)
#fill_spectrum_thread = threading.Thread(target=fill_spectrum_buffer, args=([fpga]))

recv_from_PIC_thread.start()
process_RFSoC_request_thread.start()
sending_data_thread.start()
saving_spectra_thread.start()
#fill_spectrum_thread.start()

#except:
#	conn.close()
#	PIC_s.close()
#	print("Program interrupted\n")
