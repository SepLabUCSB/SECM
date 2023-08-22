from tkinter import *
from tkinter.ttk import *



class HoppingPopup():
    def __init__(self, GUI):
        self.GUI = GUI
        self.master = self.GUI.master
        self.ready = False
            
    def make_popup(self):
        self.window = Toplevel()
        frame = Frame(self.window)
        frame.grid(row=0, column=0)
        
        self.n_scans = StringVar(value='1')
        self.move_dist = StringVar(value='100')
        
        Label(frame, text='Number of scans: ').grid(row=0, column=0, sticky=(W,E))
        Label(frame, text='Movement between scans: ').grid(row=1, column=0, sticky=(W,E))
        
        Entry(frame, textvariable=self.n_scans, width=6).grid(row=0, column=1, sticky=(W,E))
        Entry(frame, textvariable=self.move_dist, width=6).grid(row=1, column=1, sticky=(W,E))
        
        Label(frame, text='um').grid(row=1, column=2, sticky=(W))
        
        Button(frame, text='OK', command=self.OK).grid(row=2, column=1, sticky=(W,E))
        
        self.window.wait_window()
        
    def OK(self):
        self.ready = True
        self.window.destroy()
    
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
