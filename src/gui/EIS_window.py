from tkinter import *
from tkinter.ttk import *
import numpy as np
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..utils.utils import focus_next_widget, run


def make_EIS_window(gui, master_frame):
    
    # frame = Frame(master_frame)
    # frame.grid(column=0, row=0)
    
    frame = master_frame
    
    Label(frame, text='DC bias:').grid(column=1, row=0, sticky=(E))
    Label(frame, text='Scan from...').grid(column=1, row=1, sticky=(E))
    Label(frame, text='To...').grid(column=1, row=2, sticky=(E))
    Label(frame, text='Collect:').grid(column=1, row=3, sticky=(E))
    Label(frame, text='Cycles:').grid(column=1, row=4, sticky=(E))
    Label(frame, text='Amplitude:').grid(column=1, row=5, sticky=(E))
    Label(frame, text='').grid(column=1, row=6) # blank space
    
    
    DC_field = Text(frame, height=1, width=1)
    DC_field.grid(column=2, row=0, sticky=(E,W))
    DC_field.insert('1.0', '0')
    DC_field.bind('<Tab>', focus_next_widget)
    DC_field.bind('<Return>', focus_next_widget)
    
    f0_field = Text(frame, height=1, width=1)
    f0_field.grid(column=2, row=1, sticky=(E,W))
    f0_field.insert('1.0', '1')
    f0_field.bind('<Tab>', focus_next_widget)
    f0_field.bind('<Return>', focus_next_widget)
    
    f1_field = Text(frame, height=1, width=7)
    f1_field.grid(column=2, row=2, sticky=(E,W))
    f1_field.insert('1.0', '1000')
    f1_field.bind('<Tab>', focus_next_widget)
    f1_field.bind('<Return>', focus_next_widget)
    
    n_pts_field = Text(frame, height=1, width=5)
    n_pts_field.grid(column=2, row=3, sticky=(E,W))
    n_pts_field.insert('1.0', '18')
    n_pts_field.bind('<Tab>', focus_next_widget)
    n_pts_field.bind('<Return>', focus_next_widget)
    
    n_cycles_field = Text(frame, height=1, width=5)
    n_cycles_field.grid(column=2, row=4, sticky=(E,W))
    n_cycles_field.insert('1.0', '1')
    n_cycles_field.bind('<Tab>', focus_next_widget)
    n_cycles_field.bind('<Return>', focus_next_widget)
    
    amp_field = Text(frame, height=1, width=5)
    amp_field.grid(column=2, row=5, sticky=(E,W))
    amp_field.insert('1.0', '20')
    amp_field.bind('<Tab>', focus_next_widget)
    amp_field.bind('<Return>', focus_next_widget)
    
    
    Label(frame, text='mV').grid(column=3, row=0, sticky=(W))
    Label(frame, text='Hz').grid(column=3, row=1, sticky=(W))
    Label(frame, text='Hz').grid(column=3, row=2, sticky=(W))
    Label(frame, text='points').grid(column=3, row=3, sticky=(W))
    Label(frame, text='mVpp').grid(column=3, row=5, sticky=(W))   
        
    Label(frame, text='').grid(column=2, row=6)
    
    Button(frame, text='Run EIS', command=gui.run_EIS).grid(
        column=2, row=7, columnspan=2, sticky=(E,W))  
    
    Button(frame, text='Record Correction Factors', 
           command=gui.run_EIS_corrections).grid(
           column=2, row=8, columnspan=2, sticky=(E,W))
                                            
    EIS_params = {'E0':DC_field,
                  'f0':f0_field,
                  'f1':f1_field,
                  'n_pts':n_pts_field,
                  'n_cycles':n_cycles_field,
                  'amp':amp_field}
    
    return EIS_params


