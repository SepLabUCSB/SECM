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


# files = [
# "Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_006_05_15_EISDataPoint1.txt",
# "Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_006_05_15_EISDataPoint2.txt",
# "Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_006_05_15_EISDataPoint3.txt",
# "Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_006_05_15_EISDataPoint4.txt",
# "Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_006_05_15_EISDataPoint5.txt"]

files = [
"Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_015_40_00_EISDataPoint5.txt",
"Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_015_40_00_EISDataPoint1.txt",
"Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_015_40_00_EISDataPoint2.txt",
"Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_015_40_00_EISDataPoint3.txt",
"Z:/Projects/Brian/7 - SECCM/20240229 BR7 GCD 5xEISwait/export/0229_015_40_00_EISDataPoint4.txt"]

files.sort()


times = [15*i for i in range(len(files))]


def square_axes(ax):
    mini = min(*ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    # mini = -0.1
    # maxi = 5.5
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)
    

def plot(file, ax, time, *args, **kwargs):
    with open(file, 'r') as f:
        if f.read(1) == '<':
            skiprows=1
        else:
            skiprows=0
    f, re, im = np.loadtxt(file, unpack=True, skiprows=skiprows)
    ax.plot(re/1e9, -im/1e9, 'o-', label=f'{time} s', *args, **kwargs)
    # ax.text(re[0]/1e9-0.2, 4.4, f'{time} s',
    #         ha='left', va='bottom', rotation=45, *args, **kwargs)



colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(files)))
fig, ax = plt.subplots(figsize=(5,5), dpi=300)
for i in range(len(files)):
    plot(files[i], ax, times[i], color=colors[i])

# ax.set_xticks([0,1,2,3,4,5])
# ax.set_yticks([0,1,2,3,4,5])
ax.set_xlabel(r"Z'/ G$\Omega$")
ax.set_ylabel(r"Z''/ G$\Omega$")
bbox_to_anchor=[1.0,0.5,0.5,0.5]
ax.legend(bbox_to_anchor=bbox_to_anchor)
square_axes(ax)



## 5x EIS with poor electrical contact
## Plot D and j0 vs time

D  = np.array([2.29E-15,2.26E-15,3.14E-15,2.18E-15,1.78E-15])
Rd_err = np.array([2.3787e-001,4.8438e-001,1.8528e-001,4.4924e-001,3.0653e-001])
Cd_err = np.array([3.1545e-002,3.7411e-002,2.3963e-002,2.5997e-002,3.0623e-002])
D_err = np.sqrt(Rd_err**2 + Cd_err**2)
D_err *= D

j0 = np.array([35.66,17.97,53.42,12.05,16.06])
j0_dev = np.array([7.0858e-002,7.2929e-002,6.9623e-002,4.5615e-002,4.8984e-002])
j0_dev *= j0
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

fig, ax = plt.subplots()
ax.set_xlabel('Time/ s')
ax.plot(times, D, '-', color=colors[0], alpha=0.5)
ax.errorbar(times, D, yerr=D_err, fmt='o', color=colors[0], capsize=3)
ax.set_yscale('log')
ax.set_yticks([1e-15,1e-14,1e-13])
ax.set_ylim(3.7064314041636337e-16, 1e-13)
ax.set_ylabel(r'$D_{Na}$/ $m^{2}$ $s^{-1}$')


fig, ax = plt.subplots()
ax.set_xlabel('Time/ s')
ax.axhline(.6, ls='--', color='black', alpha=0.4)
ax.axhline(173.1, ls='--', color='black', alpha=0.4)
ax.plot(times, j0*10, 'o-', color=colors[0], alpha=0.5)
ax.errorbar(times, j0*10, yerr=j0_dev*10, fmt='o', color=colors[0], capsize=3)
ax.text(1, (9.6+173.1)/2, s='Fig. 4a range', va='center', alpha=0.5)
ax.set_ylabel(r'$j_{0}$/ A $m^{-2}$')
ax.set_yticks([0,150,300,450,600])

    





