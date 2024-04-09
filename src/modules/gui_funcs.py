from tkinter import *
from tkinter.ttk import *





def OptionMenuStringVar(frame, options,row,col,sticky,idx=0):
    var = StringVar()
    menu = OptionMenu(frame, var, options[idx],*options)
    menu.grid(row=row, column=col, sticky=sticky)
    return var, menu


def EntryStringVar(frame, width, row, col, sticky, bind_key=None,
                   bind_func=None):
    var = StringVar()
    entry = Entry(frame, width=width, textvariable=var)
    entry.grid(row=row, column=col, sticky=sticky)
    if bind_key:
        entry.bind(bind_key, bind_func)
    return var, entry
    


