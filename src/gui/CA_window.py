from tkinter import *
from tkinter.ttk import *
from functools import partial

from ..utils.utils import focus_next_widget, run



def make_CA_window(gui, master_frame):
    
    frame = Frame(master_frame)
    frame.grid(column=1, row=1)
    
    Label(frame, text='Test').grid(column=2, row=2, sticky=(E))
    
    Button(frame, text='Poll ADC',
           command=partial(run, gui.master.ADC.polling)
           ).grid(column=2, row=8)
    Button(frame, text='Run Custom',
           command=partial(run, gui.run_custom)
           ).grid(column=2, row=9)
    Button(frame, text='+100um',
           command=partial(gui.master.PicoMotor.move_y, 100)
           ).grid(column=2, row=10)
    Button(frame, text='-100um',
           command=partial(gui.master.PicoMotor.move_y, -100)
           ).grid(column=2, row=11)
        
    return



