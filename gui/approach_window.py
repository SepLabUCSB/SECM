from tkinter import *
from tkinter.ttk import *
import numpy as np
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from utils.utils import focus_next_widget, run


def make_approach_window(gui, master_frame):
    
    frame = Frame(master_frame)
    frame.grid(column=1, row=1)
    
    ttk.Label(frame, text='    ').grid(column=1, row=1)
    ttk.Label(frame, text='Cutoff = ').grid(column=2, row=2, sticky=(E))
    ttk.Label(frame, text='    ').grid(column=5, row=3)
    ttk.Label(frame, text='    ').grid(column=5, row=4)
    
    I_field = Text(frame, height=1, width=1)
    I_field.grid(column=3, row=2, sticky=(E,W))
    I_field.insert('1.0', '2')
    I_field.bind('<Tab>', focus_next_widget)
    
    Label(frame, text='pA').grid(column=4, row=2, sticky=(W))
    
    
    Button(frame, text='Acquire', 
           command=gui.run_approach_curve).grid(column=3, row=4)
    
    ttk.Label(frame, text='    ').grid(column=5, row=5)
    
def func(): print('running')

if __name__ == '__main__':
    root = Tk()
    root.title('test')
    frame = Frame(root)
    frame.grid(column=0, row=0, sticky=(N, S, E, W))
       
    make_approach_window(None, frame)   
    
    root.mainloop()



