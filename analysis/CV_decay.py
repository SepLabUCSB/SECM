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


   

def CV_decay_analysis(CVDataPoint, n):
    '''
    Returns fraction current (at negative limit) decayed after n cycles
    '''
    true_n = n            # Make local copy of any args
    if true_n == '':      # Passed args are used as dictionary keys for storing the result
        true_n = 0        # DO NOT modify n or else we can't access the result in the CVDataPoint
    true_n = int(true_n)
    
    if not hasattr(CVDataPoint, 'analysis'):
        CVDataPoint.analysis = {}
    
    if (CV_decay_analysis, n) in CVDataPoint.analysis.keys():
        # Already did this function at this condition
        return CVDataPoint
        
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        val = 0.0
        CVDataPoint.analysis[(CV_decay_analysis, n)] = val
        return CVDataPoint
    
        
    t, V, I = CVDataPoint.data
    dt = np.mean(np.diff(t[:1000]))
    t = np.arange(t[0], dt*len(t), dt)
    
    arr = -(np.abs(V - min(V)) - max(V))
    peaks, props = find_peaks(arr, height=0.01)
    peak_currs = I[peaks]
    peak_currs /= peak_currs[0]
    if true_n >= len(peak_currs):
        true_n = -1
    
    val = peak_currs[true_n]
    
    CVDataPoint.analysis[(CV_decay_analysis, n)] = val
    return CVDataPoint





