from tkinter import *
from tkinter.ttk import *
import numpy as np
from functools import partial

from utils.utils import focus_next_widget, run


def make_approach_window(gui, master_frame):
    
    frame = Frame(master_frame)
    frame.grid(column=1, row=1)
    
    ttk.Label(frame, text='Voltage: ').grid(column=2, row=1, sticky=(E))
    
    V_field = Text(frame, height=1, width=1)
    V_field.grid(column=3, row=1, sticky=(E,W))
    V_field.insert('1.0', '400')
    V_field.bind('<Tab>', focus_next_widget)
    
    Label(frame, text='mV').grid(column=4, row=1, sticky=(W))
    
    ttk.Label(frame, text='    ').grid(column=1, row=1)
    ttk.Label(frame, text='Cutoff: ').grid(column=2, row=2, sticky=(E))
    ttk.Label(frame, text='    ').grid(column=5, row=3)
    ttk.Label(frame, text='    ').grid(column=5, row=4)
    
    I_field = Text(frame, height=1, width=1)
    I_field.grid(column=3, row=2, sticky=(E,W))
    I_field.insert('1.0', '3')
    I_field.bind('<Tab>', focus_next_widget)
    
    Label(frame, text='pA').grid(column=4, row=2, sticky=(W))
    
    
    ttk.Label(frame, text='Height: ').grid(column=2, row=3, sticky=(E))
    Z_field = Text(frame, height=1, width=1)
    Z_field.grid(column=3, row=3, sticky=(E,W))
    Z_field.insert('1.0', '80')
    Z_field.bind('<Tab>', focus_next_widget)
    Label(frame, text='um').grid(column=4, row=3, sticky=(W))
    
    
    ttk.Label(frame, text='Speed: ').grid(column=2, row=4, sticky=(E))
    speed_field = Text(frame, height=1, width=1)
    speed_field.grid(column=3, row=4, sticky=(E,W))
    speed_field.insert('1.0', '2')
    speed_field.bind('<Tab>', focus_next_widget)
    Label(frame, text='um/s').grid(column=4, row=4, sticky=(W))
    
    Button(frame, text='Approach', 
           command=gui.run_approach_curve).grid(column=3, row=5)
   
    Button(frame, text='Retract',
           command=gui.run_retract).grid(column=3, row=6)
    
    Button(frame, text='Automatic Approach',
           command=gui.run_automatic_approach).grid(
               row=7, column = 3, columnspan=2, sticky=(W))
    
    ttk.Label(frame, text='    ').grid(column=5, row=5)
    
    approach_params = {'voltage': V_field,
                       'cutoff': I_field,
                       'z_height': Z_field,
                       'approach_speed': speed_field,}
    
    return approach_params
    


if __name__ == '__main__':
    root = Tk()
    root.title('test')
    frame = Frame(root)
    frame.grid(column=0, row=0, sticky=(N, S, E, W))
       
    make_approach_window(None, frame)   
    
    root.mainloop()



