import os
import numpy as np
import matplotlib.pyplot as plt
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']


# files = ["Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_40_25_EISDataPoint1.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_40_25_EISDataPoint2.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_40_25_EISDataPoint3.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_40_25_EISDataPoint4.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_40_25_EISDataPoint5.txt"]

# files = ["Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_45_75_EISDataPoint1.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_45_75_EISDataPoint2.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_45_75_EISDataPoint3.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_45_75_EISDataPoint4.txt",
# "Z:/Projects/Brian/7 - SECCM/20240216 BR7 GCA 1x 5xEISwait then 11x CVEIS/export/0216_001_45_75_EISDataPoint5.txt"]

files = ["Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint5.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint1.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint2.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint3.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint4.txt"
]

times = [10, 20, 50, 100, 200]
# times = [15*i for i in range(len(files))]


def square_axes(ax):
    mini = min(*ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    # mini = -0.1
    # maxi = 2.1
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)
    

def plot(file, ax, *args, **kwargs):
    with open(file, 'r') as f:
        if f.read(1) == '<':
            skiprows=1
        else:
            skiprows=0
    f, re, im = np.loadtxt(file, unpack=True, skiprows=skiprows)
    ax.plot(re/1e9, -im/1e9, *args, **kwargs)



colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(files)))
fig, ax = plt.subplots(figsize=(5,5), dpi=300)
for i in range(len(files)):
    plot(files[i], ax, 'o-', color=colors[i], label=f'{times[i]} mV')

# ax.set_xticks([0,2.5,5,7.5,10])
# ax.set_yticks([0,2.5,5,7.5,10])
ax.set_xlabel(r"Z'/ G$\Omega$")
ax.set_ylabel(r"Z''/ G$\Omega$")
ax.legend()
square_axes(ax)

