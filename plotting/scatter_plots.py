import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import numpy as np
import pandas as pd
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

file = r'Z:/Projects/Brian/7 - SECCM all PB particles/analysis.xlsx'
df = pd.read_excel(file)
lengths, Ds, sigmas, j0s = df['l'], df['D'], df['sigma'], df['j0']
D_error = df['D_error']
j0_error = df['j0_error']


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


fig, ax = plt.subplots()
ax.errorbar(lengths, j0s, yerr=j0_error*10, color=colors[3], fmt='o',
            alpha=0.5, capsize=3)
ax.scatter(lengths, j0s, color=colors[3], marker='o')
ax.set_xticks([300,500,700,900])
ax.set_yticks([0,50,100,150,200])

ax.set_xlabel('Particle size/ nm')
ax.set_ylabel(r'$j_{0}$/ A $m^{-2}$')





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

fig, ax = plt.subplots()
ax.errorbar(j0s, Ds, xerr=j0_error*10, yerr=D_error,color=colors[4], 
            fmt='o', alpha=0.5, capsize=3)
ax.scatter(j0s, Ds, color=colors[4])
ax.set_yscale('log')
ax.set_ylabel(r'$D_{Na}$/ $m^{2}$ $s^{-1}$')
ax.set_xlabel(r'$j_{0}$/ A $m^{-2}$')
ax.set_xticks([0,50,100,150,200])
ax.set_yticks([1e-15,1e-14,1e-13])
print(ax.get_ylim())




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

# fig, ax = plt.subplots()
# ax.scatter(lengths, df['Qdl']/1e-12, color=colors[0], marker='o')
# # ax.set_yscale('log')
# ax.set_xlabel('Particle size/ nm')
# ax.set_ylabel(r'$Q_{dl}$/ pF $s^{\alpha-1}$')
# # ax.set_ylim(0, 1)
# ax.set_xticks([300,500,700,900])
# # ax.set_yticks([0,2,4,6,8])
