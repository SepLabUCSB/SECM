import numpy as np
import matplotlib.pyplot as plt
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']


# file1 = r'Z:/Projects/Brian/7 - SECCM/20231207 BR30 GC D/exports/002_20_30_EISDataPoint1.txt'
file1 = r'Z:/Projects/Brian/7 - SECCM/20231010 BR7 PB/eis.csv'
file2 = r'Z:/Projects/Brian/7 - SECCM all PB particles/EIS_200mV_noNP2.asc'


def plot(file, ax, *args, **kwargs):
    f, re, im = np.loadtxt(file, delimiter='\t', unpack=True, skiprows=1)
    ax.plot(re/1e9, -im/1e9, *args, **kwargs)
    
def square_axes(ax):
    mini = min(*ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    mini = -0.1
    maxi = 2.1
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)

def make_plots(file1, file2):
    fig, ax = plt.subplots(figsize=(5,5), dpi=300)
    plot(file2, ax, 'o-', color='grey', alpha=0.8, label='Substrate')
    plot(file1, ax, 'o-', color=colors[0], label='PB NP')
    square_axes(ax)
    ax.set_xlabel(r"Z'/ G$\Omega$")
    ax.set_ylabel(r"Z''/ G$\Omega$")
    ax.legend()
    ax.set_title(file1.split('/')[-1], pad=20)


fig, ax = plt.subplots(figsize=(5,5), dpi=300)
# colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(files)))
# for i, file in enumerate(files):
#     plot(file, ax, 'o-', color=colors[i], label=f'{10*i} s')
plot(file2, ax, 'o-', color='grey', alpha=0.8)
plot(file1, ax, 'o-', color=colors[0])
square_axes(ax)
ax.set_xlabel(r"Z'/ G$\Omega$")
ax.set_ylabel(r"Z''/ G$\Omega$")
ax.set_xticks([0,0.5,1,1.5,2])
ax.set_yticks([0,0.5,1,1.5,2])
ax.legend()
# ax.set_title('1010_003_70_10')
