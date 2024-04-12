import os
import numpy as np
import matplotlib.pyplot as plt
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']



files = ["Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint5.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint1.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint2.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint3.txt",
"Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_2_004_75_75_EISDataPoint4.txt"
]

# files = ["Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_002_75_10_EISDataPoint5.txt",
# "Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_002_75_10_EISDataPoint1.txt",
# "Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_002_75_10_EISDataPoint2.txt",
# "Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_002_75_10_EISDataPoint3.txt",
# "Z:/Projects/Brian/7 - SECCM/20240226 BR7 GCA 5xEISamps/export/0226_002_75_10_EISDataPoint4.txt"
# ]


voltages = [10, 20, 50, 100, 200]


def square_axes(ax):
    mini = min(*ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    # mini = -0.1
    # maxi = 2.1
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)
    

def plot(file, ax, offset, text, color, *args, **kwargs):
    with open(file, 'r') as f:
        if f.read(1) == '<':
            skiprows=1
        else:
            skiprows=0
    f, re, im = np.loadtxt(file, unpack=True, skiprows=skiprows)
    re /= 1e9
    im /= -1e9
    ax.plot(re + offset, im, color=color, *args, **kwargs)
    center = offset + (min(re) + max(re))/2
    ax.text(center, min(im)-0.25, text, color=color, ha='center', va='top')
    return f, re, im



colors = plt.cm.Blues(np.linspace(0.5, 1, len(files)))
fig, ax = plt.subplots(figsize=(10,5), dpi=300)
offset = -1
for i in range(len(files)):
    f, re, im = plot(files[i], ax, offset, f'{voltages[i]}'+r' $mV_{pp}$',
                     colors[i], 'o-')
    offset += max(re)
    offset += 0.5

# ax.set_xticks([0,2.5,5,7.5,10])
# ax.set_yticks([0,2.5,5,7.5,10])
ax.set_xlabel(r"Z'/ G$\Omega$")
ax.set_ylabel(r"Z''/ G$\Omega$")

# square_axes(ax)
ax.set_xticks([])
ax.set_yticks([])
lim = ax.get_xlim()
ax.set_xlim(-2, 18)
ax.set_ylim(-1, 9)
minx, maxx = ax.get_xlim()
miny, maxy = ax.get_ylim()

def scale(val, mini, maxi):
    return (val - mini)/(maxi-mini)


xpos = -1
ypos = 5.5
l = 2

ax.axvline(x = xpos, ymin=scale(ypos, miny, maxy), ymax=scale(ypos+l, miny, maxy), color='k')
ax.axhline(y = ypos, xmin=scale(xpos, minx, maxx), xmax=scale(xpos+l, minx, maxx), color='k')
ax.text(xpos+l/2, ypos-0.1, r'2 G$\Omega$', ha='center', va='top')



fig, ax = plt.subplots()
for i in range(len(files)):
    f, re, im = plot(files[i], ax, 0, '', colors[i], 'o-')
ax.set_xlabel(r"Z'/ G$\Omega$")
ax.set_ylabel(r"Z''/ G$\Omega$")
ax.set_xticks([0,2,4,6])
ax.set_yticks([0,2,4,6])
square_axes(ax)
