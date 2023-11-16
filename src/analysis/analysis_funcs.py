from tkinter import *
from tkinter.ttk import *
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

def get_functions():
    '''
    Dictionary of {name: (func, description)}
    '''
    return {
        'CV decay': (CV_decay_analysis,
                    'Fractional current (at negative limit) decayed after n cycles.\nInput format: "n" = cycle number (starting from 0)'),
        'Threshold current': (threshold_current_analysis,
                    'Voltage at which x current is first reached.\nInput format: "x" = current threshold'),
        'Threshold current decay': (threshold_current_decay_analysis,
                    'Shift in voltage (relative to first cycle) required to reach x current after n cycles.\nInput format: "x,n"'),
        'E0 finder': (E0_finder_analysis,
                     'Half potential of detected redox waves larger than 5 pA.\nInput: none'),
        'Peak integral (forward)': (forward_peak_integration,
                                    'Integral of the forward redox peak.\nInput: none'),
        'Peak integral (reverse)': (reverse_peak_integration,
                                    'Integral of the reverse redox peak.\nInput: none'),
        'Peak integral (ratio)': (peak_integration_ratio,
                                  'Ratio of the forward to reverse charges.\nInput: none'),
        }


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
        res = False
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



def find_peak_bounds(t, V, I, fpeak, bpeak):
    '''
    fpeak, bpeak: indices corresponding to peaks in forward and reverse scan
    
    returns: 2-tuple of 2-tuples, corresponding to L and R bounds of forward
             and reverse peaks, respectively
             
    Starting from the peak, draw flat horizontal line. Move it down until
    one side no longer intersects the data. Fix that side's bound as the last point.
    Then, draw a line from that point to the other slide of the peak. Every point
    in the peak (that has been checked so far) will be above that line. Keep stepping
    the point on the other side down, drawing a slanted line, until it reaches
    the local minimum and starts tracing back, causing the line to intersect the data
    inside of the bound. Use that last point as the other bound.
    '''
    half = len(t)//2
        
    ft, fV, fI = t[:half], V[:half], I[:half]
    bt, bV, bI = t[half:], V[half:], I[half:]
    
    # Same peak choosing parameters as in find_redox_peaks()
    min_peak_width = max(4, int(len(t)//100)) # Don't choose spiky peaks
    prominence = 5e-12   
    
    def find_bounds(I, peak, add = 0):
        if I[peak] < 0:
            I = -I + min(-I)
        lbound = rbound = peak
        found = None
        # Forward peak
        for i in range(1, min(len(I) - peak, peak) ):
            lbound = peak - i
            rbound = peak + i
            # Check left side
            if all( I[:peak] - I[lbound] >= 0):
                found = 'left'
                break
            # Check right side
            if all( I[peak:] - I[rbound] >= 0):
                found = 'right'
                break
        
        if found == 'right':
            # rbound was fixed, draw lines to set lbound
            x = np.arange(len(I))
            x2, y2 = rbound, I[rbound]
            for lbound in reversed(range(0, peak-i)):
                x1, y1 = lbound, I[lbound]

                m = (y2 - y1) / (x2 - x1)
                b = y1 - m*x1
                
                subtracted = I - (m*x + b)
                
                if min(subtracted[lbound:rbound]) < 0:
                    lbound += 1
                    break
                
        elif found == 'left':
            # lbound was fixed, draw lines to set rbound
            x = np.arange(len(I))
            x2, y2 = lbound, I[lbound]
            for rbound in reversed(range(peak+i, len(I))):
                x1, y1 = rbound, I[rbound]

                m = (y2 - y1) / (x2 - x1)
                b = y1 - m*x1
                
                subtracted = I - (m*x + b)
                
                if min(subtracted[lbound:rbound]) < 0:
                    rbound -= 1
                    break
        return lbound+add, rbound+add
    
    fbounds = find_bounds(fI, fpeak)
    rbounds = find_bounds(bI, bpeak-half, add = half)
    
    return fbounds, rbounds
    

def integrate(t, I, start_idx, end_idx):
    '''
    Integrates from start_idx to end_idx. Draws and subtracts a straight
    baseline between those two points.
    '''
    t = t[start_idx:end_idx]
    I = I[start_idx:end_idx]
    
    ln = np.linspace(I[0], I[-1], len(I))
    
    bline_I = I - ln
    
    integral = np.trapz(bline_I, x=t)
    return integral


def current_threshold(V, I, threshold):
    '''
    Returns first voltage v such that I(v) reaches or passes the threshold
    '''
    negative = False
    if threshold < V[0]:
        negative = True
    for i, v in zip(I, V):
        if negative:
            if i <= threshold:
                break
        elif not negative:
            if i >= threshold:
                break
    return v


def count_CV_cycles(V):
    '''
    Returns number of cycles present in voltage data
    '''
    # number of differently-sloped segments
    # TODO: might fail if recording at a constant voltage due to noise
    # might try: (np.diff(np.sign(np.diff(V)[abs(np.diff(V)) >= 0.001])) != 0).sum()
    # removes segments of V where the slope is very close to 0
    n_scans = (np.diff(np.sign(np.diff(V))) != 0).sum() 
    return int(np.ceil(n_scans/2))   
    
    


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


def threshold_current_analysis(CVDataPoint, thresh):
    if not hasattr(CVDataPoint, 'analysis'):
        CVDataPoint.analysis = {}
        
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        CVDataPoint.analysis[(threshold_current_analysis, thresh)] = 0.0
        return CVDataPoint
    
    if (threshold_current_analysis, thresh) in CVDataPoint.analysis.keys():
        # Already did this function at this condition
        return CVDataPoint
    
    
    d = {'p':'e-12',
         'n':'e-9',
         'u':'e-6',
         'm':'e-3'}
    
    str_thresh = thresh  # Make local copy to not overwrite analysis dict args
    for key in d.keys():
        str_thresh = str_thresh.replace(key, d[key])
    
    float_thresh = float(str_thresh)
    
    t, V, I = CVDataPoint.data
    I = savgol_filter(I, 15, 1)
    
    v = current_threshold(V, I, float_thresh)
    
    ln = matplotlib.lines.Line2D( [v, v],
                                  [min(I), float_thresh], color='black')
    
    CVDataPoint.analysis[(threshold_current_analysis, thresh)] = v
    CVDataPoint.artists = [ln]
    return CVDataPoint



def threshold_current_decay_analysis(CVDataPoint, thresh_and_n):
    '''
    thresh_and_n: string of format '-100p,1' -> threshold = -100 pA, n = 1
    Returns the change in voltage required to pass 'thresh' current after 'n'
    cycles, relative to the voltage required in the first cycle.
    '''
    if not hasattr(CVDataPoint, 'analysis'):
        CVDataPoint.analysis = {}
        
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        CVDataPoint.analysis[(threshold_current_decay_analysis, thresh_and_n)] = 0.0
        return CVDataPoint
    
    try:
        thresh, n = thresh_and_n.split(',')

        d = {'p':'e-12',
             'n':'e-9',
             'u':'e-6',
             'm':'e-3'}
        
        str_thresh = thresh  # Make local copy to not overwrite analysis dict args
        for key in d.keys():
            str_thresh = str_thresh.replace(key, d[key])
        
        float_thresh = float(str_thresh)
        int_n = int(n)
    except:
        print(f'Invalid input for analysis function: {thresh_and_n}')
        print(f"Requires both threshold and n cycles to evaluate after, i.e. '-200p,2' evaluates at -200 pA after 2 cycles")
        CVDataPoint.analysis[(threshold_current_decay_analysis, thresh_and_n)] = 0.0
        return CVDataPoint
    
    if (threshold_current_decay_analysis, thresh_and_n) in CVDataPoint.analysis.keys():
        # Already did this function at this condition
        return CVDataPoint  
    
    
    t, V, I = CVDataPoint.data
    
    
    # Find how many cycles
    n_cycles = count_CV_cycles(V)
    if n_cycles < int_n:
        print(f'Cannot evaluate after {int_n} cycles, only detected {n_cycles} in the CV')
        CVDataPoint.analysis[(threshold_current_decay_analysis, thresh_and_n)] = 0.0
        return CVDataPoint
    
    # number of points per cycle
    n_pts = len(t)//n_cycles
    
    # do threshold at 1st cycle
    cycle_1_thresh = current_threshold(V[:n_pts], I[:n_pts], float_thresh)
    
    # do threshold at nth cycle
    cycle_n_thresh = current_threshold( V[(int_n)*n_pts : (int_n + 1)*n_pts],
                                        I[(int_n)*n_pts : (int_n + 1)*n_pts],
                                        float_thresh)
    
    delta = cycle_n_thresh - cycle_1_thresh
    
    ln1 = matplotlib.lines.Line2D( [cycle_1_thresh, cycle_1_thresh],
                                   [min(I), float_thresh], color='black')
    
    ln2 = matplotlib.lines.Line2D( [cycle_n_thresh, cycle_n_thresh],
                                   [min(I), float_thresh], color='red')
    
    
    # return difference
    CVDataPoint.analysis[(threshold_current_decay_analysis, thresh_and_n)] = delta
    CVDataPoint.artists = [ln1, ln2]
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
    avgln = matplotlib.lines.Line2D( V, I, color='navy')
    CVDataPoint.analysis[(E0_finder_analysis, *args)] = E0
    CVDataPoint.artists = [pts, ln, avgln]
    return CVDataPoint




def forward_peak_integration(CVDataPoint, *args):
    '''
    Integrate forward and reverse peaks. Returns integral of forward peak
    
    Peak integrals are only calculated once (by _peak_integration), and 
    stored in the .analysis dictionary under the keys (_peak_integration, 'forward'), 
    (_peak_integration, 'reverse'), and (_peak_integration, 'ratio').
    
    These get mapped to the appropriate key (this function, these *args)
    so it can get found the same as other analysis results. 
    '''
    CVDataPoint = _peak_integration(CVDataPoint)
    CVDataPoint.analysis[(forward_peak_integration, *args)] = CVDataPoint.analysis[(_peak_integration, 'forward')]
    return CVDataPoint

def reverse_peak_integration(CVDataPoint, *args):
    '''
    Integrate forward and reverse peaks. Returns integral of reverse peak
    
    Peak integrals are only calculated once (by _peak_integration), and 
    stored in the .analysis dictionary under the keys (_peak_integration, 'forward'), 
    (_peak_integration, 'reverse'), and (_peak_integration, 'ratio').
    
    These get mapped to the appropriate key (this function, these *args)
    so it can get found the same as other analysis results. 
    '''
    CVDataPoint = _peak_integration(CVDataPoint)
    CVDataPoint.analysis[(reverse_peak_integration, *args)] = CVDataPoint.analysis[(_peak_integration, 'reverse')]
    return CVDataPoint

def peak_integration_ratio(CVDataPoint, *args):
    '''
    Integrate forward and reverse peaks. Returns ratio of forward Q/ reverse Q
    
    Peak integrals are only calculated once (by _peak_integration), and 
    stored in the .analysis dictionary under the keys (_peak_integration, 'forward'), 
    (_peak_integration, 'reverse'), and (_peak_integration, 'ratio').
    
    These get mapped to the appropriate key (this function, these *args)
    so it can get found the same as other analysis results. 
    '''
    CVDataPoint = _peak_integration(CVDataPoint)
    CVDataPoint.analysis[(peak_integration_ratio, *args)] = CVDataPoint.analysis[(_peak_integration, 'ratio')]
    return CVDataPoint


def _peak_integration(CVDataPoint):
    
    if not hasattr(CVDataPoint, 'analysis'):
        CVDataPoint.analysis = {}
        
    if 'CVDataPoint' not in CVDataPoint.__repr__():
        CVDataPoint.analysis[(_peak_integration, 'forward')] = 0.0
        CVDataPoint.analysis[(_peak_integration, 'reverse')] = 0.0
        CVDataPoint.analysis[(_peak_integration, 'ratio')] = 0.0
        return CVDataPoint
    
    if (_peak_integration, 'forward') in CVDataPoint.analysis:
        # Previously integrated this datapoint
        return CVDataPoint
    
    t, V, I = CVDataPoint.data
    I = savgol_filter(I, 15, 1)  # Do a little filtering
    peaks = find_redox_peaks(t,V,I)
    if not peaks:
        CVDataPoint.analysis[(_peak_integration, 'forward')] = 0.0
        CVDataPoint.analysis[(_peak_integration, 'reverse')] = 0.0
        CVDataPoint.analysis[(_peak_integration, 'ratio')] = 0.0
        return CVDataPoint
    
    fbounds, rbounds = find_peak_bounds(t, V, I, *peaks)
    
    forward_integral = integrate(t, I, *fbounds)
    reverse_integral = integrate(t, I, *rbounds)
    
    
    fln  = matplotlib.lines.Line2D([t[fbounds[0]], t[fbounds[1]]],
                                   [I[fbounds[0]], I[fbounds[1]]], 
                                   linestyle='--', color='orange',
                                   marker='o')
    bln  = matplotlib.lines.Line2D([t[rbounds[0]], t[rbounds[1]]],
                                   [I[rbounds[0]], I[rbounds[1]]], 
                                   linestyle='--', color='orange',
                                   marker='o')
    smoothed_data = matplotlib.lines.Line2D(t, I, color='navy')
    
    CVDataPoint.analysis[(_peak_integration, 'forward')] = forward_integral
    CVDataPoint.analysis[(_peak_integration, 'reverse')] = reverse_integral
    CVDataPoint.analysis[(_peak_integration, 'ratio')]   = abs(forward_integral/reverse_integral)
    CVDataPoint.artists = [fln, bln, smoothed_data]
    return CVDataPoint




class AnalysisFunctionSelector():
    '''
    Class which creates a popup for analysis function selection.
    '''
    def __init__(self, root):
        self.root = root
        self.functions = get_functions()
        self.selection = list(self.functions.keys())[0]
        
    def get_selection(self):
        '''
        Make the popup window, set the dropdown to the previous selected
        function (if any, default to 1st in list), and write the description
        for that function. Closing window returns the selected function object
        '''
        popup = Toplevel()
        frame = Frame(popup)
        frame = Frame(popup)
        frame.grid(row=0, column=0)
        selectionVar = StringVar()
        self.description = StringVar(value='')
        
        OptionMenu(frame, selectionVar, self.selection,
                   *list(self.functions.keys()), command=self.changed).grid(row=0, column=0)
        Label(frame, textvariable=self.description).grid(row=1, column=0)
        Button(frame, text='OK', command=popup.destroy).grid(
            row=2, column=0)
        self.changed(self.selection)
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        popup.geometry("+%d+%d" % (x, y))
        popup.wait_window()
        self.selection = selectionVar.get()
        return self.functions[self.selection][0]
    
    def changed(self, val):
        'Dropdown changed. Update the description field'
        description = self.functions[val][1]
        self.description.set(description)
        
        
        

if __name__ == '__main__':
    file = r'C:/Users/BRoehrich/Desktop/cv_data.csv'
    t, V, I = np.loadtxt(file, unpack=True, skiprows=1, delimiter='\t')
 
 