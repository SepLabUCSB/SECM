import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']


# file = r'Z:/Projects/Brian/7 - SECCM all PB particles/MEISP/1010_003_70_10_EISDataPoint1(Na).txt'
# fit = r'Z:/Projects/Brian/7 - SECCM all PB particles/MEISP/1010_003_70_10_EISDataPoint1(Na)_fit.txt'

# fit = r"Z:/Projects/Brian/7 - SECCM all PB particles/MEISP/0125_006_51_12_EISDataPoint1_fit.txt"
# file = r"Z:/Projects/Brian/7 - SECCM all PB particles/MEISP/0125_006_51_12_EISDataPoint1.txt"

# fit = r"Z:/Projects/Brian/7 - SECCM all PB particles/MEISP/0125_007_12_43_EISDataPoint1_fit.txt"
# file = r"Z:/Projects/Brian/7 - SECCM all PB particles/MEISP/0125_007_12_43_EISDataPoint1.txt"


def plot(file, ax, *args, **kwargs):
    with open(file, 'r') as f:
        if f.read(1) == '<':
            skiprows=1
        else:
            skiprows=0
    f, re, im = np.loadtxt(file, unpack=True, skiprows=skiprows)
    ax.plot(re/1e9, -im/1e9, *args, **kwargs)
    return re+1j*im

def square_axes(ax):
    mini = min(*ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)  

def calc_chi_sq(data, fit):
    # residuals = data - fit
    # chisq = np.sum(np.abs((residuals**2)/fit))
    data = np.array((np.real(data), np.imag(data)))
    fit  = np.array((np.real(fit), np.imag(fit)))
    rsq = r2_score(data, fit)
    return rsq
         
 
def make_plots(file1, file2):
    fig, ax = plt.subplots(figsize=(5,5), dpi=300)
    data = plot(file1, ax, 'o', markeredgecolor=colors[0], markersize=8, 
                markerfacecolor='none', markeredgewidth=3)
    fit  = plot(file2, ax, '--', color='black')
    rsq = calc_chi_sq(data, fit)
    square_axes(ax)
    # ticks = [0,1,2,3,4]
    # ax.set_xticks(ticks)
    # ax.set_yticks(ticks)
    ax.set_xlabel(r"Z'/ G$\Omega$")
    ax.set_ylabel(r"Z''/ G$\Omega$")
    plt.locator_params(nbins=5)
    title = file1.split('\\')[-1].replace('_EISDataPoint1.txt', '')
    title = title.replace('_EISDataPoint3.txt', '')
    print(f'{title}, {rsq}')
    ax.set_title(title, pad=10)
    fig.tight_layout()
    # fig.savefig(file1.replace('.txt', '_titled.png'))
    # plt.close()
 

folder = r'Z:\Projects\Brian\7 - SECCM all PB particles\MEISP'
data_files = [os.path.join(folder, f) for f in os.listdir(folder) 
         if (f.endswith('EISDataPoint1.txt') or f.endswith('EISDataPoint3.txt'))]
fit_files = [f.replace('.txt', '_fit.txt') for f in data_files]


for data_file, fit_file in zip(data_files, fit_files):  
    make_plots(data_file, fit_file)

# make_plots(file, fit)
    