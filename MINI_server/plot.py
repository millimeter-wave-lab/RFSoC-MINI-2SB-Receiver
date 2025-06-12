import csv
import matplotlib.pyplot as plt
import numpy as np

# Initialize lists to store Iteration and Time Difference data
iterations = []
time_differences = []
elapsed_time = []

# Load the CSV file containing time differences
csv_file = '/home/jose/Desktop/modelo final y codigos/server_final_rfsoc/2_bands_python_1024ch_times_20250411_134251.csv'

# Read the CSV file manually without using pandas
with open(csv_file, 'r') as file:
    csv_reader = csv.reader(file)
    
    # Skip the header row
    next(csv_reader)
    
    # Read each row and append the data to the respective lists
    for row in csv_reader:
        iterations.append(float(row[0]))  # First column is iteration
        time_differences.append(float(row[1]))  # Second column is time difference in ms
        elapsed_time.append(float(row[2])/60)  # Convert from seconds to minutes

# Convert to numpy arrays for easier manipulation
time_differences = np.array(time_differences)
elapsed_time = np.array(elapsed_time)

# Print average, std, max, min
print(f"Average: {np.mean(time_differences)} ms")
print(f"Standard Deviation: {np.std(time_differences)} ms")
print(f"Max: {np.max(time_differences)} ms")
print(f"Min: {np.min(time_differences)} ms")

# Detect failed readings (greater than 25 ms)
fail_threshold = 25
failed_indices = np.where(time_differences > fail_threshold)[0]

# Calculate percentage of failed readings
num_failures = len(failed_indices)
total_readings = len(time_differences)
fail_percentage = (num_failures / total_readings) * 100

print(f"Failed readings (> {fail_threshold} ms): {num_failures} / {total_readings} ({fail_percentage}%)")

# Find the moment of the first failure
if num_failures > 0:
    first_failure_time = elapsed_time[failed_indices[0]]
    print(f"First failure occurred at {first_failure_time} minutes")
else:
    print("No failures detected.")

# Plot the time differences
plt.figure(figsize=(10, 6))

# Plot a line graph of Time Difference (ms) vs Elapsed Time (min)
plt.plot(elapsed_time, time_differences, label='Measurement Latency (ms)', color='b')

# Add labels and title
plt.xlabel('Elapsed Time (min)')
plt.ylabel('Measurement Latency (ms)')
plt.title('Measurement Latency Over Time')

# Threshold line
plt.axhline(y=25, color='r', linestyle='--', label='25 ms Threshold')

# Grid, legend, and limits
plt.grid(True)
plt.ylim(0, 240)
plt.legend()
plt.tight_layout()
plt.show()
