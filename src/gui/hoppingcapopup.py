from tkinter import *
from tkinter.ttk import *
import sys
import ast


class HoppingCAPopup():
    def __init__(self):
        # self.GUI = GUI
        # self.master = self.GUI.master
        self.ready = False
            
    def make_popup(self):
        self.window = Toplevel()
        frame = Frame(self.window)
        frame.grid(row=0, column=0)
        
        self.potentials = StringVar(value = '0')
        self.times = StringVar(value = '10')
        self.n_scans = StringVar(value='1')
        self.move_dist = StringVar(value='100')
        
        Label(frame, text='Potential(s): ').grid(row=0, column=0, sticky=(W,E))
        Label(frame, text='Time(s): ').grid(row=1, column=0, sticky=(W,E))
        Label(frame, text='Number of scans: ').grid(row=2, column=0, sticky=(W,E))
        Label(frame, text='Movement between scans: ').grid(row=3, column=0, sticky=(W,E))
        
        Entry(frame, textvariable=self.potentials, width=6).grid(row=0, column=1, sticky=(W,E))
        Entry(frame, textvariable=self.times, width=6).grid(row=1, column=1, sticky=(W,E))
        Entry(frame, textvariable=self.n_scans, width=6).grid(row=2, column=1, sticky=(W,E))
        Entry(frame, textvariable=self.move_dist, width=6).grid(row=3, column=1, sticky=(W,E))
        
        Label(frame, text='V').grid(row=0, column=2, sticky=(W))
        Label(frame, text='s').grid(row=1, column=2, sticky=(W))
        Label(frame, text='μm').grid(row=3, column=2, sticky=(W))
        
        Button(frame, text='OK', command=self.OK).grid(row=4, column=1, sticky=(W,E))
        
        self.window.wait_window()
        
    def OK(self):
        self.ready = True
        self.window.destroy()
        # self.validate_responses()
        print(f'{self.potentials.get()}, {self.times.get()}, {self.n_scans.get()}, {self.move_dist.get()}')
        CA_params = self.get_CA_params()
        print(CA_params)
        # sys.exit("exit")
    
    def validate_responses(self):
        for var in [self.n_scans, self.move_dist]:
            try: 
                var = int(var.get())
            except:
                print('')
                print('Hopping mode not started.')
                print(f'Invalid input: {var.get()}')
                return False
        return True

    def get_CA_params(self):
        array = []
        voltage, t = map(ast.literal_eval, [self.potentials.get(), self.times.get()])
        try:
            float(voltage)
            v = [voltage]
        except:
            v = list(voltage)
        try:
            float(t)
            time = [t]
        except:
            time = list(t)
            
        #print (v, time)
        
        if len(v) == 1:
            for i in range(len(time)):
                g = {0: v[0], 1: time[i]}
                array.append(g)
        elif len(v) == len(time):
            for i in range(len(time)):
                g = {0: v[i], 1: time[i]}
                array.append(g)
        else:
            print('you done fucked up (Error: invalid CA inputs)')
            time = []
            v = []
            return 0,0
            
            
        par = array[0]
        voltage = par[0]
        t = par[1]
        return array

popup = HoppingCAPopup()
popup.make_popup()