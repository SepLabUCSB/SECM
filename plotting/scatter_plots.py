import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import numpy as np
import pandas as pd
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

file = r'Z:/Projects/Brian/7 - SECCM all PB particles/analysis.xlsx'
df = pd.read_excel(file)
ions, lengths, Ds, sigmas = df['Ion'], df['l'], df['D'], df['sigma']


# lengths = [650,840,560,630,650,330,320]
# Ds = [3.54541E-13,8.47248E-12,2.27316E-13,8.2161E-15,4.60441E-14,3.1688E-12,2.05647E-12]
# sigmas = [1.58648E-05,2.69173E-06,1.43591E-05,5.88001E-06,1.62017E-05,1.56106E-05,1.87396E-05]

# lengths = [650,560,630,650,330,320]
# Ds = [3.54541E-13,2.27316E-13,8.2161E-15,4.60441E-14,3.1688E-12,2.05647E-12]
# sigmas = [1.58648E-05,1.43591E-05,5.88001E-06,1.62017E-05,1.56106E-05,1.87396E-05]


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
y_vals = np.array(Ds)

# # popt, pcov = curve_fit(func, lengths, y_vals, maxfev=10000)
# popt, pcov = curve_fit(func, lengths, y_vals, maxfev=10000, 
#                         p0=(-3.68385342e-03,  4.04619681e-11),
#                         bounds=((-np.inf,-np.inf),
#                                 (0,np.inf)))
# xs = np.linspace(min(lengths)-50, max(lengths)+50, 1000)
# fits = func(xs, *popt)

# # calculate R2
# R2 = calc_R2(y_vals, func(np.array(lengths), *popt) )
# print(f'{R2=}')

fig, ax = plt.subplots()
ax.scatter(lengths[:4], y_vals[:4], color=colors[2], label='K', marker='x')
ax.scatter(lengths[4:], y_vals[4:], color=colors[2], label='Na', marker='o')
# ax.plot(xs, fits, '--', color=colors[2])
ax.set_yscale('log')
ax.set_xlabel('Particle size/ nm')
ax.set_ylabel(r'D/ $m^{2}$ $s^{-1}$')
ax.legend(frameon=True)



#######################
### sigma vs length ###
#######################

# func = linear
y_vals = np.array(sigmas)/1e-5
# popt, pcov = curve_fit(func, lengths, y_vals, maxfev=10000)
# xs = np.linspace(min(lengths)-50, max(lengths)+50, 1000)
# fits = func(xs, *popt)

# # calculate R2
# R2 = calc_R2(y_vals, func(np.array(lengths), *popt))
# print(f'{R2=}')

fig, ax = plt.subplots()
ax.scatter(lengths[:4], y_vals[:4], color=colors[3], label='K', marker='x')
ax.scatter(lengths[4:], y_vals[4:], color=colors[3], label='Na', marker='o')
# ax.plot(xs, fits/1e-5, '--', color=colors[3])
# ax.set_yscale('log')
# ax.set_yticks([1e-4,1e-5,1e-6])
ax.set_yticks([0,1,2,3,4,5])
ax.set_xlabel('Particle size/ nm')
ax.set_ylabel(r'$\sigma$/ S $cm^{-1} \times 10^{-5}$')
ax.legend(frameon=True)



#######################
###   D vs sigma    ###
#######################


fig, ax = plt.subplots()
ax.scatter(Ds[:4], sigmas[:4], color=colors[4], label='K', marker='x')
ax.scatter(Ds[4:], sigmas[4:], color=colors[4], label='Na', marker='o')
ax.set_yscale('log')
ax.set_xscale('log')
ax.set_yticks([1e-4,1e-5,1e-6])
ax.set_xticks([1e-11,1e-12,1e-13,1e-14])
ax.set_xlabel(r'D/ $m^{2}$ $s^{-1}$')
ax.set_ylabel(r'$\sigma$/ S $cm^{-1}$')

