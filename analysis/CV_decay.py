import numpy as np
from scipy.signal import find_peaks
import matplotlib.pyplot as plt


def nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]


def extract_data(file):
    t, V, I = np.loadtxt(file, skiprows=3, unpack=True)
    dt = np.mean(np.diff(t[:1000]))
    t = np.arange(t[0], dt*len(t), dt)
    return t, V, I


   

def analysis(CVDataPoint, n):
    '''
    Returns fraction current (at negative limit) decayed after n cycles
    '''
    
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        return 0.0
    
    if n == '':
        n = 0
    n = int(n)
        
    t, V, I = CVDataPoint.data
    dt = np.mean(np.diff(t[:1000]))
    t = np.arange(t[0], dt*len(t), dt)
    
    arr = -(np.abs(V - min(V)) - max(V))
    peaks, props = find_peaks(arr, height=0.01)
    peak_currs = I[peaks]
    peak_currs /= peak_currs[0]
    if n >= len(peak_currs):
        n = -1
        
    return peak_currs[n]



if __name__ == '__main__':
    file = r'C:/Users/BRoehrich/Desktop/SECCM data/20230713 region3/00_01.asc'
    t, V, I = extract_data(file)
    
    
    
    vmin, vmax = min(V), max(V)
    
    arr = -(np.abs(V - min(V)) - max(V))
    peaks, props = find_peaks(arr, height=0.01)
    
    
    fig, ax = plt.subplots(dpi=100)
    ax.plot(t, I)
    ax.plot(t[peaks], I[peaks], 'ro')





