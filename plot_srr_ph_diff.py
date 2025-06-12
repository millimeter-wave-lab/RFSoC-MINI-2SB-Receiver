import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

# Load the CSV file
csv_filename = "results/srr_8192ch_64bits.csv"  # Change this to your actual file
data = pd.read_csv(csv_filename)

# Get just the base filename
base_filename = os.path.basename(csv_filename).lower()

# Extract frequency axis
faxis = data["Frequency (MHz)"].values

# Detect type based on base filename
if base_filename.startswith("srr"):
    values = data["SRR (dB)"].values
    ylabel = "SRR (dB)"
    title = "Sideband Rejection Ratio"
    units = "dB"
    ylimits = (-5, 70)

    length = len(values)
    # Exclude center point
    values_no_dc = np.concatenate((values[:length // 2 - 1], values[length // 2 + 1:]))
    
    print(f"Average: {np.mean(values_no_dc)} {units}")
    print(f"Standard Deviation: {np.std(values_no_dc)} {units}")
    print(f"Max: {np.max(values_no_dc)} {units}")
    print(f"Min: {np.min(values_no_dc)} {units}")

elif base_filename.startswith("phase"):
    values = data["Phase Difference (degrees)"].values
    ylabel = "Phase Difference (°)"
    title = "Measured Phase Difference between IF Outputs"
    units = "°"
    ylimits = (-150, 150)  # You can adjust this range as needed

    length = len(values)
    print(f"Average LSB: {np.mean(values[:length // 2 - 1])}{units}")
    print(f"Standard Deviation LSB: {np.std(values[:length // 2 - 1])}{units}")
    print(f"Max LSB: {np.max(values[:length // 2 - 1])}{units}")
    print(f"Min LSB: {np.min(values[:length // 2 - 1])}{units}\n")

    print(f"Average USB: {np.mean(values[length // 2 + 1:])}{units}")
    print(f"Standard Deviation USB: {np.std(values[length // 2 + 1:])}{units}")
    print(f"Max USB: {np.max(values[length // 2 + 1:])}{units}")
    print(f"Min USB: {np.min(values[length // 2 + 1:])}{units}")

else:
    raise ValueError("Filename must start with 'srr' or 'phase'.")

# Plot the data
fig = plt.figure()
ax = fig.add_subplot(111)
ax.grid()
ax.plot(faxis, values, '-', color="black")

# Set labels and title
plt.xlabel('RF Frequency (MHz)')
plt.ylabel(ylabel)
plt.title(title)
ax.set_ylim(*ylimits)

# Show plot
plt.show()
