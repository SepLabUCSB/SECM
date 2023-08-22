from tkinter import *
from tkinter.ttk import *
import numpy as np
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..utils.utils import focus_next_widget, run

filter1options = ['Bessel 100 kHz', 
                  'Bessel 30 kHz', 
                  'Bessel 10 kHz']
filter2types = ['Bessel', 'Butterworth', 'Bypass']
stimfilters  = ['2 us', '20 us']
elecmodes    = ['2 Electrode', '3 Electrode']

gains = ['0.005 mV/pA',
 '0.01 mV/pA',
 '0.02 mV/pA',
 '0.05 mV/pA',
 '0.1 mV/pA',
 '0.2 mV/pA',
 '--',
 '0.5 mV/pA',
 '1 mV/pA',
 '2 mV/pA',
 '5 mV/pA',
 '10 mV/pA',
 '20 mV/pA',
 '--',
 '50 mV/pA',
 '100 mV/pA',
 '200 mV/pA',
 '500 mV/pA',
 '1000 mV/pA',
 '2000 mV/pA']

def where(l, val):
    for i, value in enumerate(l):
        if value == val:
            return i
    raise IndexError

def make_amp_window(gui, master_frame):
    
    frame = Frame(master_frame)
    figframe = Frame(master_frame)
    frame.grid(column=1, row=1)
    figframe.grid(column=2, row=1)
    
    # Column 1 #
    Label(frame, text='V-hold : ').grid(column=1, row=1, sticky=(E))
    Label(frame, text='Filter 1: ').grid(column=1, row=2, sticky=(E))
    Label(frame, text='Filter 2: ').grid(column=1, row=3, rowspan=2, sticky=(E))
    Label(frame, text='Stim. Filter: ').grid(column=1, row=5, sticky=(E))
    Label(frame, text='Electrode Mode: ').grid(column=1, row=6, sticky=(E))
    Label(frame, text='Gain: ').grid(column=1, row=7, sticky=(E))
    
    
    # Column 2 #
    Vhold = Text(frame, height=1, width=1)
    Vhold.grid(column=2, row=1, sticky=(E,W))
    Vhold.insert('1.0', '0')
    Vhold.bind('<Tab>', focus_next_widget)
    Vhold.bind('<Return>', focus_next_widget)
    
    filter1 = StringVar(frame)
    OptionMenu(frame, filter1, filter1options[2],
               *filter1options).grid(column=2, row=2, 
                                     sticky=(E,W))
    
    filter2type = StringVar(frame)
    OptionMenu(frame, filter2type, filter2types[0],
               *filter2types).grid(column=2, row=3, 
                                     sticky=(E,W))
                                     
    f2_field = Text(frame, height=1, width=5)
    f2_field.grid(column=2, row=4, sticky=(E,W))
    f2_field.insert('1.0', '0.5')
    f2_field.bind('<Tab>', focus_next_widget)
    f2_field.bind('<Return>', focus_next_widget)
    
    stimfilter = StringVar(frame)
    OptionMenu(frame, stimfilter, stimfilters[1],
               *stimfilters).grid(column=2, row=5, 
                                     sticky=(E,W))
    
    elecmode = StringVar(frame)
    OptionMenu(frame, elecmode, elecmodes[0],
               *elecmodes).grid(column=2, row=6, 
                                     sticky=(E,W))
    
    gain = StringVar(frame)
    OptionMenu(frame, gain, gains[8],
               *gains).grid(column=2, row=7, sticky=(E,W))
    
    
    # Column 3 #
    Label(frame, text='mV').grid(column=3, row=1, sticky=(W))
    Label(frame, text='kHz').grid(column=3, row=4, sticky=(W))
    
    amp_params = {'Vhold': Vhold,
                  'filter1': filter1,
                  'filter2type': filter2type,
                  'filter2': f2_field,
                  'stimfilter': stimfilter,
                  'elecmode': elecmode,
                  'gain': gain}

    Button(frame, text='Apply settings',
           command=partial(gui.set_amplifier)
           ).grid(column=2, row=8)
        
    return amp_params

def convert_to_index(amp_params):
    params = {'E Vhold': amp_params['Vhold'].get('1.0', 'end').rstrip('\n'),
              'E Filter1': where(filter1options, 
                               amp_params['filter1'].get()),
              'E F2Response': where(filter2types, 
                               amp_params['filter2type'].get()),
              'E Filter2': amp_params['filter2'].get('1.0', 'end').rstrip('\n'),
              'E StimFilter': where(stimfilters, 
                               amp_params['stimfilter'].get()),
              'E ElectrMode': where(elecmodes, 
                               amp_params['elecmode'].get()),
              'E Gain': where(gains, amp_params['gain'].get()),
              'float_gain': float(amp_params['gain'].get().split(' ')[0])}
    return params



if __name__ == '__main__':
    root = Tk()
    root.title('test')
    frame = Frame(root)
    frame.grid(column=0, row=0, sticky=(N, S, E, W))
       
    amp_params = make_amp_window(frame)    
    
    root.mainloop()



