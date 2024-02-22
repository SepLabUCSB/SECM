import numpy as np
import matplotlib.pyplot as plt
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']



# file1 = r'Z:/Projects/Brian/7 - SECCM/20231207 BR30 GC D/exports/002_20_30_CVDataPoint0.csv'
file1 = r'Z:/Projects/Brian/7 - SECCM/20231010 BR7 PB/1010_70_10_CVDataPoint0.csv'
file2 = r'Z:/Projects/Brian/7 - SECCM/20231207 BR30 GC D/exports/background.csv'

def plot(file, ax, *args, **kwargs):
    t, v, I = np.loadtxt(file, delimiter=',', unpack=True, skiprows=1)
    ax.plot(v, I/1e-12, *args, **kwargs)
    
    

fig, ax = plt.subplots(figsize=(5,5), dpi=300)

plot(file2, ax, '-', alpha=0.8, color='grey', label='Substrate')
plot(file1, ax, '-', label='PB NP')
ax.set_xlabel('E/ V vs Ag/AgCl QRCE')
ax.set_ylabel('I/ pA')
ax.set_xticks([-0.5, 0, 0.5, 1])
ax.set_yticks([-150,-75,0,75,150])
ax.legend()
# ax.set_title('1010_003_70_10', pad=20)
