import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
import os
from simulate_Z import Z_tot
from nyquist_and_fit import plot, square_axes
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']



fnames = [
    '1010_003_70_10_EISDataPoint1.txt',
    '0226_002_55_15_EISDataPoint3.txt',
    '0226_002_75_10_EISDataPoint3.txt',
    ]

df = pd.read_excel(r'Z:/Projects/Brian/7 - SECCM all PB particles/analysis.xlsx')
df = df[df['Qf'] != 0]
fnames = df['File'].to_list()

freqs = np.logspace(-0.01, 3.2, 100)

def get_error_region(DataFrame, name, ax):
    df = DataFrame[DataFrame['File'].str.contains(name.replace('.txt', ''))]
    varnames = ['Rs', 'Rct', 'Qdl', 'phi', 'Cd', 'Rd']
    values     = {s:df[s].to_numpy()[0] for s in varnames}
    deviations = {s:df[f'{s}_dev'].to_numpy()[0]*values[s] for s in varnames} 
          
    Zs = []  
    Z_fit = np.conjugate(Z_tot(freqs*2*np.pi,values['Rs'], values['Rct'], values['Qdl'], 
                  values['phi'], values['Cd'], values['Rd']))      
    upper_bound = Z_fit.copy()
    lower_bound = Z_fit.copy()
    print(name)
    for _ in range(10000):
        rand = np.random.uniform
        vals = {s:values[s]+np.random.uniform(-2,2)*deviations[s] for s in values}
        
        Z = np.conjugate(Z_tot(freqs*2*np.pi,vals['Rs'], vals['Rct'], vals['Qdl'], vals['phi'],
                  vals['Cd'], vals['Rd']))
        
        Zs.append(Z)
        
        # for i in range(len(Z)):
        #     if (Z[i] - Z_fit[i]) > (upper_bound[i] - Z_fit[i]):
        #         upper_bound[i] = Z[i]
        #     if (Z[i] - Z_fit[i]) < (lower_bound[i] - Z_fit[i]):
        #         lower_bound[i] = Z[i]
        
        def func(Z, Z_fit):
            diff = Z - Z_fit
            real_projection = np.abs(diff)*np.cos(np.angle(diff))
            return np.mean(real_projection)
            return np.mean(Z-Z_fit)
        
        
        # if func(Z, Z_fit) > func(upper_bound, Z_fit):
        #     upper_bound = Z
        # if func(Z, Z_fit) < func(lower_bound, Z_fit):
        #     lower_bound = Z
        
        # Zs.append(Z - Z_fit)
    
    Zs = np.array(Zs).T
    upper_bound = []
    lower_bound = []
    for pt in Zs:
        mean = np.mean(pt)
        re_std = np.std(np.real(pt))
        im_std = np.std(np.imag(pt))
        upper_bound.append(mean - 2*re_std + 2*im_std*1j)
        lower_bound.append(mean + 2*re_std - 2*im_std*1j)
    
    
    # bounds = [fit + np.max(r) for r,fit in zip(Zs.T, Z_fit)] 
    # lower_bounds = [fit + np.min(r) for r,fit in zip(Zs.T, Z_fit)]
    bounds = list(upper_bound)
    bounds.extend(reversed(list(lower_bound)))
    
    
    bounds = [(np.real(b)/1e9, np.imag(b)/1e9) for b in bounds]
    poly = matplotlib.patches.Polygon(bounds, color='grey', fill=1, alpha=0.3)
    ax.add_patch(poly)
    return
    # return [max(r) for r in Zs.T], [min(r) for r in Zs.T]


for name in fnames:
    data_file = f'Z:/Projects/Brian/7 - SECCM all PB particles/MEISP/{name}'
    fit_file  = data_file.replace('.txt', '_fit.txt')
    
    fig, ax = plt.subplots()
    get_error_region(df, name, ax)
    data = plot(data_file, ax, 'o', markeredgecolor=colors[0], markersize=8, 
                markerfacecolor='none', markeredgewidth=3)
    fit  = plot(fit_file, ax, '--', color='black')
    square_axes(ax)
    ax.set_xlabel(r"Z'/ G$\Omega$")
    ax.set_ylabel(r"Z''/ G$\Omega$")
    plt.locator_params(nbins=5)
    fpath = r'Z:\Projects\Brian\7 - SECCM\0_figures\Nyquist 95 CI'
    savename = f'{name.replace(".txt", "_CI.png")}'
    fpath = os.path.join(fpath, savename)
    fig.savefig(fpath)
    plt.show()

