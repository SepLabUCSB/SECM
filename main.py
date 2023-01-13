from tkinter import *
from tkinter import ttk
import threading
import time
from functools import partial
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


from heka_io import master, HekaReader, HekaWriter
# from gui import *
from gui.CV_window import make_CV_window
from utils.utils import run

    
'''
TODO:
    Lock thread - i.e. make only one button call an object at a time
    Fix gui imports
    
    HEKA control
    - init to known state
    - store current amplifier state
    - amplifier controls
    - implement other echem funcs
    - implement data saving
    
    XYZ control
    - create test module
    
    SECM
    - make figure
    - 
    
'''

class GUI():
    
    def __init__(self, root, master):
        self.master = master
        self.root = root
        
        masterthread = run(self.master.run)
        readerthread = run(self.master.HekaReader.read_stream)
        
        root.title("SECM Controller")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0) 

        leftpanel = Frame(self.root, width=500)
        leftpanel.grid(row=0, column=0)
        
        rightpanel = Frame(self.root)
        rightpanel.grid(row=0, column=1)
        
        
        tabControl = ttk.Notebook(leftpanel)
        
        secm_frame  = Frame(tabControl)
        pstat_frame = Frame(tabControl)
        
        tabControl.add(pstat_frame, text ='Potentiostat Control')
        tabControl.add(secm_frame, text ='SECM Control')
        tabControl.pack(expand = 1, fill ="both")
          
        ttk.Label(secm_frame, text ="secm driver").grid(
            column = 0, row = 0, padx = 30, pady = 30)  

          

        ######################################
        #####                            #####
        #####   POTENTIOSTAT CONTROLS    #####                            
        #####                            #####
        ######################################
        
        
        PSTAT_TABS = ttk.Notebook(pstat_frame)
        
        amplifier_control = Frame(PSTAT_TABS)
        cv_control        = Frame(PSTAT_TABS)
        eis_control       = Frame(PSTAT_TABS)
        ca_control        = Frame(PSTAT_TABS)
        
        PSTAT_TABS.add(amplifier_control, text='Amplifier')
        PSTAT_TABS.add(cv_control, text='  CV  ')
        PSTAT_TABS.add(eis_control, text='  EIS  ')
        PSTAT_TABS.add(ca_control, text='  CA  ')
        PSTAT_TABS.pack(expand=1, fill='both')
        
        
        self.cv_params = make_CV_window(self, cv_control) 
        
        # readerthread = run(self.master.HekaReader.test_read)
        # writerthread = run(self.master.HekaWriter.test_write)
        
        
    def run_CV(self):
        #unpack params
        cv_params = self.cv_params.copy()
        E0 = cv_params['E0'].get('1.0', 'end')
        E1 = cv_params['E1'].get('1.0', 'end')
        E2 = cv_params['E2'].get('1.0', 'end')
        E3 = cv_params['Ef'].get('1.0', 'end')
        v  = cv_params['v'].get('1.0', 'end')
        t0 = cv_params['t0'].get('1.0', 'end')
        vals = [E0, E1, E2, E3, v, t0]
        try:
            E0, E1, E2, E3, v, t0 = [float(val) for val in vals]
        except:
            print('invalid CV inputs')
        self.master.HekaWriter.setup_CV(E0, E1, E2, E3, v, t0)
        self.master.HekaWriter.run_CV_loop()
    
    def printout(self):
        print(self.master.modules)
        time.sleep(3)
        print(self.master.modules)
        return
            
                                                        
        
                                                            
                
    







if __name__ == '__main__':
    master = master()
    reader = HekaReader(master)
    writer = HekaWriter(master)
    root = Tk()
    gui = GUI(root, master)
    
    root.mainloop()
    gui.master.willStop = True
    