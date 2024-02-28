import numpy as np
import matplotlib.pyplot as plt
plt.style.use('style.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']


f = np.logspace(0.5,5,100)
w = 2*np.pi*f


def Zsph(w, Cd, Rd):
    s = 1j*w
    Z = np.tanh( np.sqrt(3*Cd*Rd*s) ) / (np.sqrt(3*Cd*s/Rd) - (1/Rd)*np.tanh(np.sqrt(3*Cd*Rd*s)))
    return Z


def Q(w, C, phi):
    s = 1j*w
    return 1/(C*s**phi)


def Z_tot(w, Rs, Rct, Cdl, phi, Cd, Rd):
    
    Z_Cdl  = Q(w,Cdl,phi)
    Z_diff = Zsph(w, Cd, Rd) 
    
    Z_farad = Rct + Z_diff
    Z_cir = Rs + 1/( (1/Z_farad) + (1/Z_Cdl) )
    return Z_cir

def square_axes(ax):
    mini = min(*ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)     

Rs = 2.38E+07	
Rct = 4e8	
Cdl = 1E-12	
phi = 1	
Rd = 1e9	
Cd = 1e-10



fig, ax = plt.subplots()
Z = Z_tot(w, Rs, Rct, Cdl, phi, Cd, Rd)
for i, (phi,Cd) in enumerate(([(0.80,1e-9),
                              (0.85,5e-10),
                              (0.90,1e-10),
                              (0.95,5e-11)])):
    Z = Z_tot(w, Rs, Rct, Cdl, phi, Cd, Rd)
    alpha = 2/(5-i)
    ax.plot(np.real(Z)/1e9, -np.imag(Z)/1e9, '-', color=colors[0], alpha=alpha)


square_axes(ax)
ticks = [0,0.25,0.5,0.75,1]
ax.set_xticks(ticks)
ax.set_yticks(ticks)
ax.set_xlabel(r"Z'/ G$\Omega$")
ax.set_ylabel(r"Z''/ G$\Omega$")
    



