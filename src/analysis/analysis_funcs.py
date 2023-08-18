import matplotlib
import numpy as np
from scipy.signal import find_peaks, savgol_filter


'''
Analysis functions should all:
    - Take a DataPoint object and some arguments as inputs
    - Return a DataPoint object with attribute DataPoint.analysis
    - DataPoint.analysis is a dictionary. Keys are (function, *args) tuples.
      Values are floats, which can be displayed on the heatmap.
    - Artists to draw on the right figure should be appended to DataPoint.artists
'''

def nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]


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



def E0_finder_analysis(CVDataPoint, *args):
    '''
    Assumes 1 CV cycle!!!
    
    Determines the locations of the forward and backward peak currents
    
    Returns E0 = halfway between them
    '''
    if not hasattr(CVDataPoint, 'analysis'):
        CVDataPoint.analysis = {}
        
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        CVDataPoint.analysis[(E0_finder_analysis, *args)] = 0.0
        return CVDataPoint
    
    t, V, I = CVDataPoint.data
    dt = np.mean(np.diff(t[:1000]))
    t = np.arange(t[0], dt*len(t), dt)
    
    half = len(I)//2
    
    current = savgol_filter(I, 15, 1)  # Do a little filtering
    if np.mean(np.diff(V[:20])) < 0:
        current = -current  # Makes sure forward scan peak is positive
    
    forw = current[:half]
    back = -current[half:] - min(-current[half:])  # get everything positive
    
    
    def choose_most_prominent(arr, prominence):
        peaks, props = find_peaks(arr, prominence = prominence)
        if len(peaks) == 0:
            return None, None
        idx = [i for i, prom in enumerate(props['prominences']) 
               if prom == max(props['prominences'])][0]
        peak = np.array([peaks[idx]])
        prop = {key: np.array([arr[idx]]) for key, arr in props.items()}
        return peak, prop
    
    fpeak, fprop = choose_most_prominent(forw, prominence=10e-12)
    bpeak, bprop = choose_most_prominent(back, prominence=10e-12)
    
    if (not fpeak) or (not bpeak):
        CVDataPoint.analysis[(E0_finder_analysis, *args)] = 0.0
        return CVDataPoint
    
    # find peak voltages and get E0
    f_peak_idx = fpeak
    b_peak_idx = bpeak + half
    
    E0 = (V[f_peak_idx] + V[b_peak_idx])/2
    E0 = E0[0]
    
    # draw point artists on peaks
    x = [V[f_peak_idx], V[b_peak_idx]]
    y = [I[f_peak_idx], I[b_peak_idx]]
    pts= matplotlib.lines.Line2D(x, y, linestyle='', marker='o', color='red')
    ln = matplotlib.lines.Line2D([E0, E0], 
                                 [I[f_peak_idx], I[b_peak_idx]],
                                 color='black')
    
    CVDataPoint.analysis[(E0_finder_analysis, *args)] = E0
    CVDataPoint.artists = [pts, ln]
    return CVDataPoint
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    





