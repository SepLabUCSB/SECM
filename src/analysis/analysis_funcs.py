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

#############################################
########                             ########
########       HELPER FUNCTIONS      ########
########                             ########
#############################################


def nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]


def find_peaks_all(x, **kwargs):
    if np.mean(np.diff(x)) < 0:
        x = -x + min(-x)
    return find_peaks(x, **kwargs)


def fixed_vals(arr, half):
    if len(arr) > 0:
        if type(arr[0]) == np.int64:
            arr = np.array([np.int64(val + half) for val in arr])
    return arr


def find_redox_peaks(t, V, I):
    '''
    Analyze CV data. Returns pair of indices corresponding to the location of
    the most prominent forward peak and its corresponding reverse peak.
    '''
        
    half           = len(t)//2
    min_peak_width = max(4, int(len(t)//100)) # Don't choose spiky peaks
    
    # Find prominent forward peaks
    fpeaks, fprops = find_peaks_all(I[:half], prominence=5e-12, 
                                    width=[min_peak_width,None])
        
    # Find prominent reverse peaks
    bpeaks, bprops = find_peaks_all(I[half:], prominence=5e-12, 
                                    width=[min_peak_width,None])
    bpeaks = [p + half for p in bpeaks]
    bprops = {key:fixed_vals(arr, half) for  key, arr in bprops.items()}
          
    # Match forward and reverse peaks. Choose closest peak pairs
    def isSuitable(fpeak, bpeak, V):
        # Returns True if bpeak is on the expected side of fpeak
        # I.e. bpeak is more negative if fpeak is an oxidation, bpeak is
        #      more positive if fpeak is a reduction
        direction = np.diff(V)[fpeak]
        if direction > 0:   # oxidative scan for fpeak, look for reductive bpeak
            res = True if V[bpeak] < V[fpeak] else False
        elif direction < 0: # reductive scan for fpeak, look for more oxidative bpeak
            res = True if V[bpeak] > V[fpeak] else False
        return res

    pairs = []
    for fpeak in fpeaks:
        bpeak_candidates = [bpeak for bpeak in bpeaks if 
                            isSuitable(fpeak, bpeak, V)]
        if len(bpeak_candidates) == 0:
            continue
        
        best_peak  = bpeak_candidates[0]
        best_delta = abs(V[fpeak] - V[bpeak_candidates[0]])
        for bpeak in bpeak_candidates:
            delta = abs(V[fpeak] - V[bpeak])
            if delta < best_delta:
                best_peak  = bpeak
                best_delta = delta
        
        pairs.append( (fpeak, best_peak) )
    if len(pairs) == 0:
        return None
    
    
    # Choose pair with most prominent forward peak
    valid_fpeaks, valid_bpeaks = zip(*pairs)
    valid_f_idxs = [i for i, fpeak in enumerate(fpeaks) if fpeak in valid_fpeaks]
    max_fprom = max(fprops['prominences'][valid_f_idxs])
    
    for i, (fpeak, bpeak) in enumerate(pairs):
        idx  = [idx for idx, val in enumerate(fpeaks) if val == fpeak][0]
        prom = fprops['prominences'][idx]
        if prom != max_fprom:
            continue        
        best_pair = (fpeak, bpeak)
    try:
        return best_pair
    except:
        print('error')
        return None


#############################################
########                             ########
########     MAIN ANALYSIS FUNCS     ########
########                             ########
#############################################

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
    
    try:
        arr = -(np.abs(V - min(V)) - max(V))
        peaks, props = find_peaks(arr, height=0.01)
        peak_currs = I[peaks]
        peak_currs /= peak_currs[0]
        if true_n >= len(peak_currs):
            true_n = -1
        
        val = peak_currs[true_n]
    
    except:
        val = 0.0
    
    CVDataPoint.analysis[(CV_decay_analysis, n)] = val
    return CVDataPoint


def E0_finder_analysis(CVDataPoint, *args):
    if not hasattr(CVDataPoint, 'analysis'):
        CVDataPoint.analysis = {}
        
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        CVDataPoint.analysis[(E0_finder_analysis, *args)] = 0.0
        return CVDataPoint
    
    t, V, I = CVDataPoint.data
    I = savgol_filter(I, 15, 1)  # Do a little filtering
    peaks = find_redox_peaks(t,V,I)
    if not peaks:
        CVDataPoint.analysis[(E0_finder_analysis, *args)] = 0.0
        return CVDataPoint
    fpeak, bpeak = peaks
    
    E0 = (V[fpeak] + V[bpeak])/2
    
    pts = matplotlib.lines.Line2D( [V[fpeak], V[bpeak]],
                                   [I[fpeak], I[bpeak]],
                                   linestyle='', marker='o', color='red')
    ln  = matplotlib.lines.Line2D( [E0, E0],
                                   [I[fpeak], I[bpeak]], color='black')
    CVDataPoint.analysis[(E0_finder_analysis, *args)] = E0
    CVDataPoint.artists = [pts, ln]
    return CVDataPoint

    


def E0_finder_analysis_old(CVDataPoint, *args):
    '''
    Assumes 1 CV cycle!!!
    
    Determines the locations of the forward and backward peak currents
    
    Returns E0 = halfway between them
    '''
    
    Vpp_CUTOFF = 0.6   # Don't return E0 if peak-to-peak separation exceeds this value
    
    if not hasattr(CVDataPoint, 'analysis'):
        CVDataPoint.analysis = {}
        
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        CVDataPoint.analysis[(E0_finder_analysis, *args)] = 0.0
        return CVDataPoint
    
    t, V, I = CVDataPoint.data
    dt = np.mean(np.diff(t[:1000]))
    t = np.arange(t[0], dt*len(t), dt)
    
    half = len(I)//2
    
    pos_scan_first = True
    
    current = savgol_filter(I, 15, 1)  # Do a little filtering
    if np.mean(np.diff(V[:20])) < 0:
        pos_scan_first = False
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
    
    fV = V[f_peak_idx]
    bV = V[b_peak_idx]
    
    # Check that peaks are in correct order
    if (
        (pos_scan_first and (bV > fV)) or   # Backwards (red) peak is at a more positive potential than forward (ox) peak
        (not pos_scan_first and (fV > bV))  # Backwards (ox) peak is at a more positive potential than forward (red) peak
        ):
        
        CVDataPoint.analysis[(E0_finder_analysis, *args)] = 0.0
        return CVDataPoint
    
    E0 = (fV + bV)/2
    E0 = E0[0]
    
    if (abs(V[f_peak_idx] - V[b_peak_idx]) > Vpp_CUTOFF or
        abs(V[b_peak_idx] - V[f_peak_idx]) > Vpp_CUTOFF):
        CVDataPoint.analysis[(E0_finder_analysis, *args)] = 0.0
        return CVDataPoint
    
    # draw point artists on peaks
    x = [fV, bV]
    y = [I[f_peak_idx], I[b_peak_idx]]
    pts= matplotlib.lines.Line2D(x, y, linestyle='', marker='o', color='red')
    ln = matplotlib.lines.Line2D([E0, E0], 
                                 [I[f_peak_idx], I[b_peak_idx]],
                                 color='black')
    
    CVDataPoint.analysis[(E0_finder_analysis, *args)] = E0
    CVDataPoint.artists = [pts, ln]
    return CVDataPoint
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    





