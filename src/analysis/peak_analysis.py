import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from scipy.optimize import curve_fit



class CV:
    def __init__(self, t, V, I):
        self.t = t
        self.V = V
        self.I = I
        
    def find_peaks(self):
        # Check that there are 2 cycles
        
        half = len(self.I)//2
        
        fpeak, fprops = find_peaks(abs(self.I[:half]))



def extract_data(file):
    scan_rate = 0.1
    t, V, I = np.loadtxt(file, skiprows=3, unpack=True)
    
    # Fix times
    dV = np.mean(abs(np.diff(V)))
    dt = dV/scan_rate
    
    t = np.arange(0, dt*len(V), dt)
    
    return t, V, I


def choose_most_prominent(peaks, props):
        
    idx = [i for i, prom in enumerate(props['prominences']) 
           if prom == max(props['prominences'])][0]
    
    peak = np.array([peaks[idx]])
    prop = {key: np.array([arr[idx]]) for key, arr in props.items()}
    
    return peak, prop


def linear(x, m, b):
    return m*x + b


def get_baseline_pts(peak, prop, I):
    # fig, ax = plt.subplots(dpi=100)
    # ax.plot(I, '.')
    # ax.plot(peak, I[peak], 'ro')
    # ax.plot([peak, peak], [I[peak], I[peak] - prop['prominences']], 'k-')
    # ax.plot(prop['right_bases'], I[prop['right_bases']], 'ko')
    
    
    right_base = prop['right_bases'][0]
    left_base  = peak[0]
    
    for i in reversed(range(peak[0])):
        val = I[i]
        if I[peak] - val < prop['prominences']:
            continue
        I_slice = I[i:right_base]
        bline = np.linspace(I[i], I[right_base], right_base - i)
        
        if any([val < 0 for val in I_slice - bline]):
            left_base = i + 1
            break
    
    xbline = np.linspace(left_base, right_base, right_base - left_base)
    ybline = np.linspace(I[left_base], I[right_base], right_base - left_base)
    
    # ax.plot(xbline, ybline, 'k--')
            
    return left_base, right_base


def peak_integration(t, V, I):
    
    
    
    half = len(I)//2
    fcurr = I[:half]
    bcurr = -I[half:] - min(-I[half:]) # Gets everything positive and peak pointing up
    
    fpeaks, fprops = find_peaks(fcurr, prominence=0.5e-12)        
    bpeaks, bprops = find_peaks(bcurr, prominence=0.5e-12)
    
    if (len(fpeaks) == 0) or (len(bpeaks) == 0):
        bpeak = np.array([p + half for p in bpeaks])
        peaks = np.concatenate((fpeaks, bpeaks))
        return 0,0
      
    fpeak, fprop = choose_most_prominent(fpeaks, fprops)
    bpeak, bprop = choose_most_prominent(bpeaks, bprops)
    
    peaks  = np.concatenate((fpeak, bpeak+half))
    fig, ax = plt.subplots()
    ax.plot(V, I)
    ax.plot(V[peaks], I[peaks], 'ko')
    
    f_left, f_right = get_baseline_pts(fpeak, fprop, fcurr)
    b_left, b_right = get_baseline_pts(bpeak, bprop, bcurr)
    b_left  += half
    b_right += half
        
    
    
    
    fxs = V[f_left:f_right]
    fys = np.linspace(I[f_left], I[f_right], len(fxs))
    
    bxs = V[b_left:b_right]
    bys = np.linspace(I[b_left], I[b_right], len(bxs))
    
    ax.plot(fxs, fys, 'k--')
    ax.plot(bxs, bys, 'k--')
    
    
    Qf = np.trapz(I[f_left:f_right] - fys, x=fxs)
    Qb = np.trapz(I[b_left:b_right] - bys, x=bxs)
    
    Qf /= np.mean(np.diff(t))
    Qb /= np.mean(np.diff(t))
    
    dE = V[peaks[0]] - V[peaks[1]]
    
    ax.set_xlim(-0.25, 1.05)
    ax.set_ylim(-3e-12, 20e-12)
    ax.text(-0.1, 1.5e-11, f'$\Delta$E = {dE*1000:0.1f} mV\nQf = {Qf/1e-12:0.1f} pC\nQb = {Qb/1e-12:0.1f} pC')
    
    
    
    return bpeak, bprop


def run(file):
    t, V, I = extract_data(file)
    I = savgol_filter(I, 5, 1)
    
    I -= min(I)
    
    peaks, props = peak_integration(t, V, I)
    return

def analysis():
    print('OK')
    return
 

if __name__ == '__main__':   
    plt.style.use('C:/Users/BRoehrich/Desktop/git/SECM/secm.mplstyle')
    files = ["C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/05_01.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/03_06.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/03_07.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/03_08.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/03_09.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_01.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_02.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_03.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_04.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_05.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_06.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_07.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_08.asc",
    "C:/Users/BRoehrich/Desktop/SECCM data/20230706 region1/04_09.asc"]
    
    
    for file in files:
        run(file)


        


