from tkinter import *
from tkinter.ttk import *
import numpy as np
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from utils.utils import focus_next_widget, run


def make_EIS_window(gui, master_frame):
    
    # frame = Frame(master_frame)
    # frame.grid(column=0, row=0)
    
    frame = master_frame
    
    ttk.Label(frame, text='Scan from...').grid(column=1, row=1, sticky=(E))
    Label(frame, text='To...').grid(column=1, row=2, sticky=(E))
    Label(frame, text='Collect:').grid(column=1, row=3, sticky=(E))
    Label(frame, text='').grid(column=1, row=4) # blank space
    Label(frame, text='Amplitude:').grid(column=1, row=5, sticky=(E))
    Label(frame, text='').grid(column=1, row=6) # blank space
    
    
    f0_field = Text(frame, height=1, width=1)
    f0_field.grid(column=2, row=1, sticky=(E,W))
    f0_field.insert('1.0', '1')
    f0_field.bind('<Tab>', focus_next_widget)
    
    f1_field = Text(frame, height=1, width=5)
    f1_field.grid(column=2, row=2, sticky=(E,W))
    f1_field.insert('1.0', '1000')
    f1_field.bind('<Tab>', focus_next_widget)
    
    n_pts_field = Text(frame, height=1, width=5)
    n_pts_field.grid(column=2, row=3, sticky=(E,W))
    n_pts_field.insert('1.0', '18')
    n_pts_field.bind('<Tab>', focus_next_widget)
    
    amp_field = Text(frame, height=1, width=5)
    amp_field.grid(column=2, row=5, sticky=(E,W))
    amp_field.insert('1.0', '20')
    amp_field.bind('<Tab>', focus_next_widget)
    
    
    
    Label(frame, text='Hz').grid(column=3, row=1, sticky=(W))
    Label(frame, text='Hz').grid(column=3, row=2, sticky=(W))
    Label(frame, text='points').grid(column=3, row=3, sticky=(W))
    Label(frame, text='mVpp').grid(column=3, row=5, sticky=(W))
    
    EIS_params = {'f0':f0_field,
                  'f1':f1_field,
                  'n_pts':n_pts_field,
                  'amp':amp_field}
    
    Button(frame, text='Run EIS', command=
            partial(run, gui.run_EIS)).grid(column=2, row=7,
                                           sticky=(E,W))  
    
    return EIS_params


if __name__ == '__main__':
    class this_gui:
        def __init__(self):
            self.run_CV = lambda x:0
            self.master = self
            self.abort = lambda x:0
            
    # gui = this_gui()   
    root = Tk()
    root.title('test')
    frame = Frame(root)
    # frame.grid(column=0, row=0, sticky=(N, S, E, W))
       
    EIS_params = make_EIS_window(frame)    
    print(EIS_params)
    
    root.mainloop()



