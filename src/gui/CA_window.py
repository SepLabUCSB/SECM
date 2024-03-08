from tkinter import *
from tkinter.ttk import *
from functools import partial
import numpy as np
from ..utils.utils import focus_next_widget, run
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def make_CA_window(gui, master_frame):
    
    frame = Frame(master_frame)
    figframe = Frame(master_frame)
    frame.grid(column=1, row=1)
    figframe.grid(column=2, row=1)
    
    Label(frame, text='Eapp = ').grid(column=1, row=1, sticky=(E))
    
    e1 = Label(frame, text='t = ')
    e1.grid(column=1, row=2, sticky=(E))
    
    e2 = Label(frame, text='Frequency = ')
    e2.grid(column=1, row=3, sticky=(E))
    
    Eapp_field = Text(frame, height=1, width=1)
    Eapp_field.grid(column=2, row=1, sticky=(E,W))
    Eapp_field.insert('1.0', '0')
    Eapp_field.bind('<Tab>', focus_next_widget)
    Eapp_field.bind('<Return>', focus_next_widget)
    
    t_field = Text(frame, height=1, width=5)
    t_field.grid(column=2, row=2, sticky=(E,W))
    t_field.insert('1.0', '100')
    t_field.bind('<Tab>', focus_next_widget)
    t_field.bind('<Return>', focus_next_widget)
    
    f_field = Text(frame, height=1, width=5)
    f_field.grid(column=2, row=3, sticky=(E,W))
    f_field.insert('1.0', '1000')
    f_field.bind('<Tab>', focus_next_widget)
    f_field.bind('<Return>', focus_next_widget)
    
    
    Label(frame, text='V').grid(column=3, row=1, sticky=(W))
    Label(frame, text='s').grid(column=3, row=2, sticky=(W))
    Label(frame, text='Hz').grid(column=3,row=3, sticky = (W))
    
  
    ca_params = {'Eapp':Eapp_field,
                 't':t_field,
                 'Frequency':f_field}
    
    Button(frame, text='Run CA', command=
           partial(run, gui.run_CA)).grid(column=2, row=8)
        
    
    
    fig = plt.Figure(figsize=(3,2), dpi=50)
    ax = fig.add_subplot(111)
    canvas = FigureCanvasTkAgg(fig, master=figframe)
    canvas.get_tk_widget().grid(row=0, column=0)
    make_CA_fig(ax)
    
    return ca_params

def make_CA_fig(ax):
    arr = np.concatenate((
        np.zeros(10),
        np.linspace(0,1,10),
        np.linspace(1,-1,20),
        np.linspace(-1,0,10)        
        ))
    ax.plot(arr)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(0, 0.1, 'E app')
    ax.text(0, -0.3, 't  -->')
    ax.text(22,0.8, 'Frequency')


if __name__ == '__main__':
    root = Tk()
    root.title('test')
    frame = Frame(root)
    frame.grid(column=0, row=0, sticky=(N, S, E, W))
       
    make_CA_window(frame)    
    
    root.mainloop()
