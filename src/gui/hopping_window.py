from tkinter import *
from tkinter.ttk import *
import numpy as np
from functools import partial

from ..utils.utils import focus_next_widget, run

methods = ['CV', 'CV then EIS', 'CV then 2x EIS', 'CV then 5x EIS', 'Custom']


def make_hopping_window(gui, master_frame):
    
    frame = Frame(master_frame)
    frame.grid(column=1, row=1)
    
    Label(frame, text='    ').grid(column=1, row=0)
    Label(frame, text='Length: ').grid(column=2, row=1, sticky=(E))
    Label(frame, text='Z height: ').grid(column=2, row=2, sticky=(E))
    Label(frame, text='Points per line: ').grid(column=2, row=3, sticky=(E))
    Label(frame, text='    ').grid(column=5, row=4)
    Label(frame, text='    ').grid(column=5, row=5)
    
    size_field = Text(frame, height=1, width=1)
    size_field.grid(column=3, row=1, sticky=(E,W))
    size_field.insert('1.0', '50')
    size_field.bind('<Tab>', focus_next_widget)
    size_field.bind('<Return>', focus_next_widget)
    
    Z_field = Text(frame, height=1, width=1)
    Z_field.grid(column=3, row=2, sticky=(E,W))
    Z_field.insert('1.0', '80')
    Z_field.bind('<Tab>', focus_next_widget)
    Z_field.bind('<Return>', focus_next_widget)
    
    points_field = Text(frame, height=1, width=1)
    points_field.grid(column=3, row=3, sticky=(E,W))
    points_field.insert('1.0', '10')
    points_field.bind('<Tab>', focus_next_widget)
    points_field.bind('<Return>', focus_next_widget)
    
    Label(frame, text='μm').grid(column=4, row=1, sticky=(W))
    Label(frame, text='μm').grid(column=4, row=2, sticky=(W))
    Label(frame, text='(n x n grid)').grid(column=4, row=3, sticky=(W))
    
    method = StringVar()
    OptionMenu(frame, method, methods[0],
               *methods).grid(column=3, row=4, 
                                     sticky=(E,W))
    
    Button(frame, text='Hopping mode scan', 
           command=gui.run_hopping).grid(column=3, row=5)
    
    Button(frame, text='Multi hopping scan', 
           command=gui.run_multi_hopping).grid(column=3, row=6)
        
    hopping_params = {
        'size': size_field,
        'Z': Z_field,
        'n_pts': points_field,
        'method':method,
        }
    return hopping_params
    

if __name__ == '__main__':
    root = Tk()
    root.title('test')
    frame = Frame(root)
    frame.grid(column=0, row=0, sticky=(N, S, E, W))
       
    make_approach_window(None, frame)   
    
    root.mainloop()



