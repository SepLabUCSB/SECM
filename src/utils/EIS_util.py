import struct
import numpy as np
import matplotlib.pyplot as plt

'''
Functions for generating multi-sin EIS waveforms and saving
them in HEKA-compatible format.
'''


def nearest(value, array):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]


def generate_tpl(f0, f1, n_pts, n_cycles, mVpp, fname, Z=None):
    '''
    Wraps generate_waveform, make_time_domain, and write_tpl_file
    
    Inputs:
        f0: float, starting frequency (Hz)
        f1: float, ending frequency (Hz)
        n_pts: int, number of frequencies to measure
        n_cycles: int, number of cycles of the lowest frequency to measure
        mVpp: float, (freq dependent) peak-peak amplitude
        fname: file path to write to
        Z: (optional) array. If given, used to "optimize" waveform
        
    Outputs:
        None. Writes waveform to fname
    '''
    # Validate inputs
    assert(f1 > f0 > 0),    'EIS input error: must have f1 > f0 > 0.'
    assert(f1 > n_pts*f0), f'EIS input error: cannot fit {n_pts} points between {f0} and {f1} Hz because for FFT-EIS, all frequencies must be integer multiples of the lowest frequency ({f0} Hz).'
    assert(mVpp > 0),       'EIS input error: amplitude must be positive'
    assert(n_cycles >= 1),  'EIS input error: n_cycles must be >= 1'
    
    mVpp /= 1000 # PATCHMASTER actually needs it in V
    mVpp *= 10   # PATCHMASTER divides voltages from tpl by 10 for some reason...
    mVpp /= 2    # Make it peak-to-peak instead of amplitude
    
    freqs, phases, mVpp = generate_waveform(f0, f1, n_pts, mVpp)
    
    # if Z is None:
    #     v = make_time_domain(freqs, phases, mVpp)
    # else:
    v = optimize_waveform_default(freqs, phases, n_cycles, mVpp)  
    write_tpl_file(v, fname)
    # print(f'Wrote waveform to {fname}')
    return freqs


def generate_waveform(f0, f1, n_pts, mVpp):
    '''
    f0: float, starting frequency (Hz)
    f1: float, ending frequency (Hz)
    n_pts: int, number of frequencies to measure
    mVpp: float, peak-peak amplitude
    '''
    
    # Generate array of frequencies
    freqs = np.logspace(np.log10(f0), np.log10(f1), n_pts)
    
    # All frequencies must be interger multiples of the lowest frequency,
    # and should not be 2nd harmonics of each other
    # Avoid harmonics of 60 Hz as well (US mains power frequencies)
    
    base_freq = f0
    valid_freqs = [n*base_freq for n in range(1, 1 + int(f1//base_freq))]
    
    
    for i in range(n_pts):
        f = freqs[i]
        idx, f = nearest(f, valid_freqs) # Find closest interger multiple
        
        while ( (f in freqs[:i]) 
               or (f%60 == 0)                       # 60 Hz harmonics
               or any([f/set_freq == 2 for set_freq in freqs[:i]]) # 2nd harmonic of lower freq
              ):
            idx += 1
            try:
                f = valid_freqs[idx]
            except:
                break   
        freqs[i] = f
    
    phases = [np.random.randint(-180, 180) for _ in freqs]
        
    return freqs, phases, mVpp
        

def make_time_domain(freqs, phases, n_cycles, mVpp):
    '''
    Total measurement duration is n_cycles * 1/min(freqs): 
    n cycle at the lowest requested frequency.
    
    Number of points needd it duration*sample rate. For now, sample rate is 
    fixed at 50 kHz. In the future the sample rate will be chosen based
    on the maximum requested frequency (srate >= 10* max(freqs) )
    '''

    if type(mVpp) not in (list, np.ndarray):
        mVpp = [mVpp for _ in freqs]
    
    sample_rate = 50000 # TODO: set this dynamically, choose between i.e. 10, 25, 100kHz
    
    N = (1/min(freqs)) * sample_rate * n_cycles
    N = int(np.ceil(N)) # collect 1 extra point if N is not an integer
    v = np.zeros(N)
    t = np.linspace(0, n_cycles * 1/min(freqs), N)
    for freq, phase, amp in zip(freqs, phases, mVpp):
        v += amp*np.sin(2*np.pi*freq*t + phase)
    
    v *= max(mVpp)/max(v) # rescale to set max Vpp
        
    return v
        



def optimize_waveform(freqs, phases, mVpp, Z):
    '''
    Use previously recorded Z to adjust the amplitude for each sine wave.
    
    Summed waveform still has Vpp = mVpp
    '''
    Z = np.asarray(Z)
    amp_factor = 1/np.absolute(Z)
    mVpp = mVpp * (amp_factor/max(amp_factor))
    return make_time_domain(freqs, phases, mVpp)


def optimize_waveform_default(freqs, phases, n_cycles, mVpp):
    '''
    Make |V| ~ 1/sqrt(f)
    '''
    amp_factor = 1/np.sqrt(freqs)
    mVpp = mVpp * amp_factor/max(amp_factor)
    return make_time_domain(freqs, phases, n_cycles, mVpp)


def get_sample_rate(fmax):
    '''
    Returns sampling rate (int) based on maximum recorded frequency
    '''
    if fmax <= 2500:
        return 10000
    if fmax <= 10000:
        return 25000
    if fmax <= 25000:
        return 100000
    return 200000
        

def plot_freqs(freqs, amps):
    x = np.arange(min(freqs), max(freqs) + min(freqs), min(freqs)/10)    
    y = np.zeros(len(x))
    
    for i, freq in enumerate(freqs):
        idx, _ = nearest(freq, x)
        y[idx] = amps[i]
    
            
    plt.plot(x, y)
    plt.xscale('log')
    plt.xlabel('Frequency/ Hz')
    plt.ylabel('Amplitude/ a.u.')
    

def write_tpl_file(voltages, fname):
    '''
    voltages: list or array of time-domain voltages
    fname: file to write to
    '''
    # write list of short floats to .tpl file
    buff = struct.pack('f'*len(voltages), *voltages)
    with open(fname, 'wb') as f:
        f.write(buff)
        
        
        
        
if __name__ == '__main__':        
    freqs, phases, mVpp = generate_waveform(1, 1000, 18, 20)
    
    # v = make_time_domain(freqs, phases, mVpp)
    v = optimize_waveform_default(freqs, phases, mVpp)
    
    # Hz = 50000 #sampling rate
    # A = -0.514   #amplitude
    # A *= 2
    # x = 73  #time
    # t = np.linspace(0, x, Hz*x)
    
    # #half of t datapoints
    # half = int(len(t)/2)
    
    # #creates waveform
    # y1 = A*np.sqrt(abs(1-(2*(t[:half]/x))**2))
    # y2 = -A*np.sqrt(abs(1-(2*(t[half:]/x-1))**2))
    
    # v = list(y1) + list(y2)
    # plt.plot(v)
    # write_tpl_file(v, r'D:/Brian/circular_1.tpl')
        






