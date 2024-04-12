import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit
import numpy as np
import pandas as pd
import os
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

file = r'Z:/Projects/Brian/7 - SECCM all PB particles/analysis.xlsx'
df = pd.read_excel(file)
df = df[df['Qf'] != 0]
lengths, Ds, sigmas, j0s = df['l'], df['D'], df['sigma'], df['j0']
D_error = df['D_error']
j0_error = df['j0_error']
Qf, Qrev, Epp = df[['Qf', 'Qrev', 'Epp']].values.T
Rs_dev, Rct_dev, Qdl_dev, phi_dev = df[['Rs_dev','Rct_dev','Qdl_dev','phi_dev']].values.T

# Qf, Qrev, Epp = df['Qf'], df['Qrev'], df['Epp']


def linear(x, a, b):
    return a*x + b

def logfunc(x, a, b):
    return (b*10**(a*x))

def calc_R2(y_vals, fit_vals):
    residuals = y_vals - fit_vals
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum( (y_vals- np.mean(y_vals) )**2 )
    return 1 - (ss_res/ss_tot)


#######################
###  D  vs length   ###
#######################
# func = logfunc
# fitdf = df[df['D'] < 2e-12]
# x_vals = np.array(fitdf['l'])
# y_vals = np.array(fitdf['D'])

# popt, pcov = curve_fit(func, lengths, y_vals, maxfev=1000)
# popt, pcov = curve_fit(func, x_vals, y_vals, maxfev=10000, 
#                         p0=(3.68385342e-03,  4.04619681e-13),
#                         bounds=((-np.inf,-np.inf),
#                                 (np.inf,np.inf)))
# xs = np.linspace(min(lengths)-50, max(lengths)+50, 1000)
# fits = func(xs, *popt)

# # # calculate R2
# R2 = calc_R2(y_vals, func(np.array(x_vals), *popt) )
# r = np.sqrt(R2)
# print(f'{r=}')

# y_vals = Ds

# fig, ax = plt.subplots()
# ax.errorbar(lengths, y_vals, yerr=D_error, color=colors[2], fmt='o', 
#             alpha=0.5, capsize=3)
# ax.scatter(lengths, y_vals, color=colors[2])
# # ax.plot(xs, fits, '--', color=colors[2])
# ax.set_yscale('log')
# ax.set_xlabel('Particle size/ nm')
# ax.set_ylabel(r'$D_{Na}$/ $m^{2}$ $s^{-1}$')
# ax.set_xticks([300,500,700,900])
# # ax.legend(frameon=True)




#######################
###   j0 vs length  ###
#######################


# fig, ax = plt.subplots()
# ax.errorbar(lengths, j0s, yerr=j0_error*10, color=colors[3], fmt='o',
#             alpha=0.5, capsize=3)
# ax.scatter(lengths, j0s, color=colors[3], marker='o')
# ax.set_xticks([300,500,700,900])
# ax.set_yticks([0,50,100,150,200])

# ax.set_xlabel('Particle size/ nm')
# ax.set_ylabel(r'$j_{0}$/ A $m^{-2}$')





#######################
### sigma vs length ###
#######################

# func = linear
# y_vals = np.array(sigmas)/1e-5
# # popt, pcov = curve_fit(func, lengths, y_vals, maxfev=10000)
# # xs = np.linspace(min(lengths)-50, max(lengths)+50, 1000)
# # fits = func(xs, *popt)

# # # calculate R2
# # R2 = calc_R2(y_vals, func(np.array(lengths), *popt))
# # print(f'{R2=}')

# fig, ax = plt.subplots()
# ax.scatter(lengths, y_vals, color=colors[3], label='Na', marker='o')
# # ax.plot(xs, fits, '--', color=colors[3])
# # ax.set_yscale('log')
# # ax.set_yticks([1e-4,1e-5,1e-6])
# # ax.set_yticks([0,1,2,3,4,5])
# ax.set_xlabel('Particle size/ nm')
# ax.set_ylabel(r'$\sigma$/ S $cm^{-1} \times 10^{-5}$')
# ax.set_xticks([300,500,700,900])
# # ax.legend(frameon=True)


#######################
###   D vs j0    ###
#######################


# popt, pcov = curve_fit(linear, j0s, Ds,
#                        p0=(3.68385342e-03,  4.04619681e-13))
# xs = np.linspace(0.1,20,1000)
# fits = linear(xs, *popt)
# R2 = calc_R2(Ds, linear(j0s, *popt))
# print(f'{R2=}')

# fig, ax = plt.subplots()
# ax.errorbar(j0s, Ds, xerr=j0_error*10, yerr=D_error,color=colors[4], 
#             fmt='o', alpha=0.5, capsize=3)
# ax.scatter(j0s, Ds, color=colors[4])
# ax.set_yscale('log')
# ax.set_ylabel(r'$D_{Na}$/ $m^{2}$ $s^{-1}$')
# ax.set_xlabel(r'$j_{0}$/ A $m^{-2}$')
# ax.set_xticks([0,50,100,150,200])
# ax.set_yticks([1e-15,1e-14,1e-13])




#######################
###   D vs sigma    ###
#######################


# fig, ax = plt.subplots()
# ax.scatter(sigmas, Ds, color=colors[4], label='Na', marker='o')
# ax.set_yscale('log')
# # ax.set_xscale('log')
# # ax.set_yticks([1e-4,1e-5,1e-6])
# # ax.set_xticks([1e-11,1e-12,1e-13,1e-14])
# ax.set_ylabel(r'D/ $m^{2}$ $s^{-1}$')
# ax.set_xlabel(r'$\sigma$/ S $cm^{-1}$')


##################################
###  EIS parameters vs length  ###
##################################

# 'Rs', 'Rct', 'Qdl', 'phi'
var = 'phi'

fig, ax = plt.subplots()
ax.errorbar(lengths, df[f'{var}'], yerr=df[f'{var}_dev']*df[f'{var}'], 
            color=colors[0], fmt = 'o', alpha=0.5, capsize=3)
ax.scatter(lengths, df[f'{var}'], color=colors[0], marker='o')
# ax.set_yscale('log')
ax.set_xlabel('Particle size/ nm')
ax.set_ylabel(r'$\alpha$')
ax.set_ylim(0, 1)
ax.set_xticks([300,500,700,900])
# ax.set_yticks([0,2,4,6,8])


##################################
###       Charge and Epp       ###
##################################


# xvars = [Qf, Epp, lengths]
# xlabels = ['Oxidation Charge/ pC', r'$\Delta E_{pp}$/ V', 'Particle size/ nm']

# yvars = [Qrev, j0s, Ds/1e-14, df['Rs']/1e6, df['Rct']/1e9, df['Qdl']/1e-12, df['Cd']/1e-12]
# ylabels = ['Reduction Charge/ pC', r'$j_{0}$/ A $m^{-2}$', 
#             r'$D_{Na}$/ $\times 10^{-14} m^{2}$ $s^{-1}$', r'$R_{s}$/ M$\Omega$', 
#             r'$R_{ct}$/ G$\Omega$', r'$Q_{dl}$/ pF $s^{\alpha-1}$', r'$C_{d}$/ pF']

# # all_vars=[Qf, Epp, lengths, Qrev, j0s, Ds, df['Rs'], df['Rct'], df['Qdl'], df['Cd']]

# # all_labels =  ['Oxidation Charge/ pC', r'$\Delta E_{pp}$', 'Particle size/ nm',
# #              'Reduction Charge/ pC', r'$j_{0}$/ A $m^{-2}$', 
# #             r'D/ $m^{2}$ $s^{-1}$', r'$R_{s}$/ $\Omega$', 
# #             r'$R_{ct}$/ $\Omega$', r'$Q_{dl}$/ F $s^{\alpha-1}$', r'$C_{diff}$/ F']


# output_folder = r'Z:\Projects\Brian\7 - SECCM\0_figures\correlations'
# i = 0


# fig, axes = plt.subplots(len(xvars),len(yvars),
#                           figsize=(len(yvars)*4,len(xvars)*4))
# for xvals, xlabel in zip(xvars, xlabels):
#     for yvals, ylabel in zip(yvars, ylabels):
    
# # for j, (xvals, xlabel) in enumerate(zip(all_vars, all_labels)):
# #     for yvals, ylabel in zip(all_vars[j:], all_labels[j:]):

#         popt, pcov = curve_fit(linear, xvals, yvals)
#         R2 = calc_R2(yvals, linear(xvals, *popt))
#         # if (R2 < 0.1 or R2 == 1):
#         #     continue
        
        
#         # fig, ax = plt.subplots(layout='constrained')
#         ax = axes.flatten()[i]
#         ax.plot(xvals, yvals, 'o')
#         xlocs = np.linspace(min(xvals), max(xvals), 1000)
#         ax.plot(xlocs, linear(xlocs, *popt), 'k--', label=f'$R^{2}$ = {R2:0.3f}')
#         # ax.set_title(f'{R2=:0.3f}')
#         ax.set_xlabel(xlabel)
#         ax.set_ylabel(ylabel)
#         ax.xaxis.set_major_locator(plt.MaxNLocator(5))
#         ax.yaxis.set_major_locator(plt.MaxNLocator(5))
#         ax.legend()
#         # fig.tight_layout()
#         # plt.savefig(os.path.join(output_folder, f'{i}.png'))
#         i += 1













