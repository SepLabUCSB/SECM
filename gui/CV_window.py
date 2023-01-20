from tkinter import *
from tkinter.ttk import *
import numpy as np
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from utils.utils import focus_next_widget, run


def make_CV_window(gui, master_frame):
    
    frame = Frame(master_frame)
    figframe = Frame(master_frame)
    frame.grid(column=1, row=1)
    figframe.grid(column=2, row=1)
    
    ttk.Label(frame, text='E0 = ').grid(column=1, row=1, sticky=(E))
    
    e1 = Label(frame, text='t0 = ')
    e1.grid(column=1, row=2, sticky=(E))
    
    e2 = Label(frame, text='E1 = ')
    e2.grid(column=1, row=3, sticky=(E))
    
    e3 = Label(frame, text='E2 = ')
    e3.grid(column=1, row=4, sticky=(E))
    
    e4 = Label(frame, text='Ef = ')
    e4.grid(column=1, row=5, sticky=(E))
    
    e5 = Label(frame, text='v = ')
    e5.grid(column=1, row=6, sticky=(E))
    
    
    E0_field = Text(frame, height=1, width=1)
    E0_field.grid(column=2, row=1, sticky=(E,W))
    E0_field.insert('1.0', '0')
    E0_field.bind('<Tab>', focus_next_widget)
    
    t0_field = Text(frame, height=1, width=5)
    t0_field.grid(column=2, row=2, sticky=(E,W))
    t0_field.insert('1.0', '5')
    t0_field.bind('<Tab>', focus_next_widget)
    
    E1_field = Text(frame, height=1, width=5)
    E1_field.grid(column=2, row=3, sticky=(E,W))
    E1_field.insert('1.0', '0.5')
    E1_field.bind('<Tab>', focus_next_widget)
    
    E2_field = Text(frame, height=1, width=5)
    E2_field.grid(column=2, row=4, sticky=(E,W))
    E2_field.insert('1.0', '-0.5')
    E2_field.bind('<Tab>', focus_next_widget)
    
    Ef_field = Text(frame, height=1, width=5)
    Ef_field.grid(column=2, row=5, sticky=(E,W))
    Ef_field.insert('1.0', '0')
    Ef_field.bind('<Tab>', focus_next_widget)
    
    v_field  = Text(frame, height=1, width=5)
    v_field.grid(column=2, row=6, sticky=(E,W))
    v_field.insert('1.0', '0.1')
    v_field.bind('<Tab>', focus_next_widget)
    
    
    Label(frame, text='V').grid(column=3, row=1, sticky=(W))
    Label(frame, text='s').grid(column=3, row=2, sticky=(W))
    Label(frame, text='V').grid(column=3, row=3, sticky=(W))
    Label(frame, text='V').grid(column=3, row=4, sticky=(W))
    Label(frame, text='V').grid(column=3, row=5, sticky=(W))
    Label(frame, text='V/s ').grid(column=3, row=6, sticky=(W))
    
    cv_params = {'E0':E0_field,
                 't0':t0_field,
                 'E1':E1_field,
                 'E2':E2_field,
                 'Ef':Ef_field,
                 'v':v_field}
    
    Button(frame, text='Run CV', command=
           partial(run, gui.run_CV)).grid(column=2, row=8)
    
    Button(frame, text='Abort', command= 
           partial(run, gui.master.HekaWriter.abort)).grid(column=2, row=9)
    
    Button(frame, text='Test', command= 
           partial(run, gui.master.HekaWriter.test_btn)
           ).grid(column=2, row=10)
    
    
    fig = plt.Figure(figsize=(3,2), dpi=50)
    ax = fig.add_subplot(111)
    canvas = FigureCanvasTkAgg(fig, master=figframe)
    canvas.get_tk_widget().grid(row=0, column=0)
    make_CV_fig(ax)
    
    return cv_params

def make_CV_fig(ax):
    arr = np.concatenate((
        np.zeros(10),
        np.linspace(0,1,10),
        np.linspace(1,-1,20),
        np.linspace(-1,0,10)        
        ))
    ax.plot(arr)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(0, 0.1, 'E 0')
    ax.text(0, -0.3, 't 0 -->')
    ax.text(22, 0.8, 'E 1')
    ax.text(42, -0.95, 'E 2')
    ax.text(46, 0.1, 'E f')
    ax.text(0, -0.95, 'v = scan rate')

if __name__ == '__main__':
    root = Tk()
    root.title('test')
    frame = Frame(root)
    frame.grid(column=0, row=0, sticky=(N, S, E, W))
       
    make_CV_window(frame)    
    
    root.mainloop()



