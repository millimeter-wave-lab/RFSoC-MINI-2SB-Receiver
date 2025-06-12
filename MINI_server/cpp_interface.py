import cpp_socket
import time
import struct
from numpy import fft
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import re

# Precompile regex pattern for efficiency
escape_pattern = re.compile(rb'\\e|\\n|\\r|\\0|\\_|\\t|\\\\')

# Mapping of escape sequences to their byte replacements
escape_map = {
    b'\\e': b'\x1b',  # Escape
    b'\\n': b'\x0a',  # Newline
    b'\\r': b'\x0d',  # Carriage Return
    b'\\0': b'\x00',  # Null
    b'\\_': b'\x20',  # Space
    b'\\t': b'\x09',  # Tab
    b'\\\\': b'\x5c'  # Backslash
}

# Function to replace matches using the escape_map
def replace_match(match):
    return escape_map[match.group(0)]

# Parámetros de medición
duration = 60 * 60  # 60 minutos en segundos

nchan = 8192

client = cpp_socket.CPPSocket("10.17.90.187", 12345)

for j in range(1):

    # Nombre del archivo CSV con timestamp
    csv_filename = f'python_{nchan}ch_times_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    # Escribir encabezado del archivo CSV
    with open(csv_filename, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(["Iteration", "Measurement Time (ms)", "Elapsed Time (s)"])

    print("Iniciando medición continua...")
    iteration = 0

    n_bytes = nchan[j] // 8 * 4

    start_time = time.time()
    time_stamps = []
    measure_times = []

    while time.time() - start_time < duration:
        
        iter_start = time.time()
        
        raw1 = np.zeros((8, nchan[j]//8))
        raw2 = np.zeros((8, nchan[j]//8))
        
        for i in range(8):    # Extract data from BRAMs blocks for each output
            
            response1 = client.send_request(f"synth0_{i} 0 {n_bytes}")
            # print(response1)
            # print(len(response1))
            raw1[i,:] = struct.unpack(f'<{nchan[j] // 8}L', response1)
            # #print(raw1[i,:])
            time.sleep(0.001)

            response2 = client.send_request(f"synth1_{i} 0 {n_bytes}")
            # # # print(len(msg_translated2))
            raw2[i,:] = struct.unpack(f'<{nchan[j] // 8}L', response2)
            time.sleep(0.001)

        interleave_i = raw1.T.ravel().astype(np.float64) 
        interleave_q = raw2.T.ravel().astype(np.float64)

        interleave_shift_i = fft.fftshift(interleave_i)
        interleave_shift_q = fft.fftshift(interleave_q)
        
        # print(interleave_shift_i)
        # print(interleave_shift_q)


        #print(len(msg_translated))
        #print(type(msg_translated))

        iter_end = time.time()

        time.sleep(0.02)

        elapsed_time = iter_end - start_time  # Tiempo transcurrido
        measurement_time = (iter_end - iter_start) * 1e3  # Tiempo que tarda la medición en milisegundos
        #print(f"Elapsed time {measurement_time}")
        # Guardar datos en el archivo CSV
        with open(csv_filename, 'a', newline='') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow([iteration, measurement_time, elapsed_time])

        iteration += 1

    print(f"Medición finalizada. Datos guardados en {csv_filename}")



# Leer datos del CSV y graficar
iterations = []
time_differences = []
elapsed_time = []

with open(csv_filename, 'r') as file:
    csv_reader = csv.reader(file)
    next(csv_reader)  # Saltar encabezado
    for row in csv_reader:
        iterations.append(int(row[0]))
        time_differences.append(float(row[1]))  # Tiempo de medición en milisegundos
        elapsed_time.append(float(row[2])/60)  # Tiempo transcurrido en minutos

# Graficar resultados
plt.figure(figsize=(10, 6))
plt.plot(elapsed_time, time_differences, label='Measurement Latency (ms)', color='b')

plt.xlabel('Elapsed Time (min)')
plt.ylabel('Measurement Latency (ms)')
plt.title('Measurement Latency Over Time')
plt.grid(True)
plt.ylim(0, 240)
plt.axhline(y=25, color='r', linestyle='--', label='25 ms')
plt.legend()
plt.tight_layout()
plt.show()