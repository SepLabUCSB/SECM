from tkinter import *
from tkinter import ttk
import threading
import time
from functools import partial
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from modules.HekaIO import HekaReader, HekaWriter
from modules.ADC import ADC
from modules.Piezo import Piezo
from modules.FeedbackController import FeedbackController
from gui import *
from utils.utils import run

    
'''
TODO:
    
    Lock thread - i.e. make only one button call an object at a time
    
    Logging
    
    File system
    - saving protocol
    - upload protocol
    
    
    HEKA control
    - create separate SECM_ pgf, analysis, etc files
    - init to known state
    - store current amplifier state
    - amplifier controls
    - implement other echem funcs
    
    XYZ control
    - create test module
    
    SECM
    - make figure
    - controller
        - point and click
        - scanning protocols
    
    - approach curve
    - const. distance scan
    - hopping mode
    - const. current, measure Z mode
    
    
    
'''

global gl_st 
gl_st = time.time()

class MasterModule():
    
    def __init__(self):
        self.willStop = False
        self.STOP = False
        self.modules = [self]
        
    def register(self, module):
        # register a submodule to master
        setattr(self, module.__class__.__name__, module)
        self.modules.append(getattr(self, module.__class__.__name__))
    
    def run(self):
        while True:
            if time.time() - gl_st > 60: 
                break
            
            for module in self.modules:
                if module.willStop:
                    self.STOP = True
                    print('master stopping')
                    return self.endState()
            time.sleep(0.5)
        
    def endState(self):
        for module in self.modules:
            if hasattr(module, 'stop'):
                module.stop()
        return
            




class GUI():
    
    def __init__(self, root, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        self.root = root
        
        
        # Always-running functions
        masterthread = run(self.master.run)
        readerthread = run(self.master.HekaReader.read_stream)
    
        self.threads = [masterthread, readerthread]
        
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
        
        
        self.cv_params        = make_CV_window(self, cv_control)
        
        self.amp_param_fields = make_amp_window(self, amplifier_control)
        self.amp_params       = {}
        
        ###  TODO: UNCOMMENT ME FOR FINAL CONFIG. STARTUP FROM KNOWN AMP. STATE ###
        # self.set_amplifier()
        ######################
    
    
    
    
    
        ######################################
        #####                            #####
        #####       SECM CONTROLS        ##### 
        #####                            #####
        ######################################
    
    
        SECM_TABS = ttk.Notebook(secm_frame)
        
        approach_curve = Frame(SECM_TABS)
        hopping_mode   = Frame(SECM_TABS)
        const_current  = Frame(SECM_TABS)
        const_height   = Frame(SECM_TABS)
        
        SECM_TABS.add(approach_curve, text=' Approach Curve ')
        SECM_TABS.add(hopping_mode, text=' Hopping ')
        SECM_TABS.add(const_current, text=' Constant I ')
        SECM_TABS.add(const_height, text=' Constant Z ')
        SECM_TABS.pack(expand=1, fill='both')
        
        
        make_approach_window(self, approach_curve)
    
    
    
    
    
    
        ######################################
        #####                            #####
        #####       CALLBACK FUNCS       #####  
        #####                            #####
        ######################################
    
        
    def set_amplifier(self):
        new_params = convert_to_index(self.amp_param_fields)
        cmds = []
        for key, val in new_params.items():
            if val != self.amp_params.get(key, None):
                cmds.append(f'{key} {val}')
        
        for cmd in cmds:
            self.master.HekaWriter.macro(cmd)
        
        self.amp_params = new_params
        return
        
    
    def run_CV(self):
        self.set_amplifier()
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
        if v > 0.1:
            print('max scan rate 100mV/s - gotta fix')
            return
        self.master.HekaWriter.setup_CV(E0, E1, E2, E3, v, t0)
        self.master.HekaWriter.run_CV_loop()
        return
    
    
    def run_approach_curve(self):
        self.set_amplifier()
    
            
                                                        
        
                                                            
                
    







if __name__ == '__main__':
    master = MasterModule()
    reader = HekaReader(master)
    writer = HekaWriter(master)
    adc    = ADC(master)
    piezo  = Piezo(master)
    fbc    = FeedbackController(master) # must be loaded last
    
    root = Tk()
    gui = GUI(root, master)
    
    root.mainloop()
    gui.willStop = True
    