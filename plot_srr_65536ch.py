import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Load both CSV files containing SRR data
data1 = pd.read_csv("results/srr_65536_1.csv")
data2 = pd.read_csv("results/srr_65536_2.csv")

# Concatenate the two DataFrames into a single dataset
combined_data = pd.concat([data1, data2])

# Remove duplicate frequency entries, if any (recommended)
combined_data = combined_data.drop_duplicates(subset="Frequency (MHz)")

# Sort the data by frequency to ensure proper ordering
combined_data = combined_data.sort_values(by="Frequency (MHz)")

# Extract the frequency and SRR values as NumPy arrays
faxis = combined_data["Frequency (MHz)"].values
values = combined_data["SRR (dB)"].values

# Compute statistics excluding the central (DC) frequency point
length = len(values)
values_no_dc = np.concatenate((values[:length // 2 - 1], values[length // 2 + 1:]))

# Print basic statistical metrics of the SRR (excluding DC)
print(f"Average: {np.mean(values_no_dc)} dB")
print(f"Standard Deviation: {np.std(values_no_dc)} dB")
print(f"Max: {np.max(values_no_dc)} dB")
print(f"Min: {np.min(values_no_dc)} dB")

# Plot the SRR over frequency
plt.figure()
plt.grid()
plt.plot(faxis, values, '-', color="black")
plt.xlabel('RF Frequency (MHz)')
plt.ylabel('SRR (dB)')
plt.title('Sideband Rejection Ratio')
plt.ylim(-5, 70)
plt.show()