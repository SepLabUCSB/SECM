import struct
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']



struct_fmt = 'f' #float
struct_len = struct.calcsize(struct_fmt)
struct_unpack = struct.Struct(struct_fmt).unpack_from


tplfile = 'C:/Users/BRoehrich/Desktop/_auto_eis-10kHz_1.tpl'

buff = []
with open(tplfile, 'rb') as f:
    while True:
        data = f.read(struct_len)
        if not data: 
            break
        s = struct_unpack(data)
        buff.append(*s)


arr = np.array(buff)
arr *= 50/(max(arr) - min(arr))


npts = 10000
fig, ax = plt.subplots(dpi=600)
ax.plot(np.linspace(0,1,npts), arr[:npts], lw=2)
ax.set_xticks([0,0.25,0.5,0.75,1])
ax.set_yticks([-30,-15,0,15,30])
ax.set_ylim(-30,30)
ax.set_xlim(0,1)
ax.set_xlabel('Time/ s')
ax.set_ylabel('Voltage/ mV')


# ftV  = np.fft.rfft(arr)[1:]
# freq = np.fft.rfftfreq(len(arr))[1:] * 10000

# fig, ax = plt.subplots()
# ax.plot(freq, np.abs(ftV), '-', color=colors[0])
# ax.set_xscale('log')
# ax.set_xlabel('Frequency/ Hz')
# ax.set_ylabel('Voltage')
# ax.set_xticks([1e0,1e1,1e2,1e3])
# ax.set_yticks([])
# locmin = matplotlib.ticker.LogLocator(base=10.0,subs=(0.2,0.4,0.6,0.8),numticks=12)
# ax.xaxis.set_minor_locator(locmin)


# tstart = 0.58
# duration = 0.02
# tbounds = (tstart, tstart+duration)
# idxbounds = [int(tbound*10000) for tbound in tbounds]
# arr_slice = arr[idxbounds[0]:idxbounds[1]]

# insax = inset_axes(ax, width='100%', height='100%',
#                     bbox_to_anchor=(0.07,0.7,0.4,0.3),  #(left, bottom, width, height)
#                     bbox_transform=ax.transAxes) 
# insax.set_xticks([])
# insax.set_yticks([])
# insax.plot(arr_slice, color=colors[0]) # Plot from 0.24 to 0.26 s

# times = np.linspace(0,1,npts)
# left, right = times[idxbounds[0]], times[idxbounds[1]]
# mean = np.mean(arr_slice)
# delta = max(arr_slice) - min(arr_slice)
# top = max(arr_slice) + 0.1*delta
# bottom = min(arr_slice) - 0.1*delta
# rect = Rectangle((left, bottom), right-left, top-bottom, ec='gray', fill=0)
# ax.add_artist(rect)
# ax.draw_artist(rect)










