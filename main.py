from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog
import time
import traceback
import tracemalloc
import json
from functools import partial
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
from modules.HekaIO import HekaReader, HekaWriter
from modules.ADC import ADC
from modules.Piezo import Piezo
from modules.FeedbackController import FeedbackController
from modules.Plotter import Plotter
from modules.DataStorage import Experiment, load_from_file
from utils.utils import run
import gui
from gui import *


matplotlib.use('TkAgg')
plt.style.use('default')

TEST_MODE = True


    
'''
TODO:
    
    Lock thread - i.e. make only one button call an object at a time
    
    Make logger!
    
    Save/ load settings file
    
    
    HEKA control
    - init to known state
    - store current amplifier state for next time controller loads
    - implement other echem funcs
    
    XYZ control
    - create test module
    
    SECM
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

SETTINGS_FILE = 'settings/DEFAULT.json'

class MasterModule():
    
    def __init__(self, TEST_MODE):
        # TEST_MODE: bool, True = record fake data
        self.willStop   = False
        self.STOP       = False
        self.ABORT      = False
        self.TEST_MODE  = TEST_MODE
        
        self.modules    = [self]
        
        self.expt = Experiment()
        
        
    def register(self, module):
        # register a submodule to master
        setattr(self, module.__class__.__name__, module)
        self.modules.append(getattr(self, module.__class__.__name__))
    
    
    def set_expt(self, expt):
        self.expt = expt
    
    
    def run(self):
        # master main loop
        while True:
            for module in self.modules:
                if module.willStop:
                    # STOP flag stops everything
                    self.STOP = True
                    self.abort()
                    print('master stopping')
                    self.endState()
                    return 
            time.sleep(0.1)
        
    
    def abort(self):
        # general callback for aborting an operation
        # submodule should call master.make_ready() after
        # aborting process
        self.ABORT = True
    
    
    def make_ready(self):
        time.sleep(1) # wait for other threads to abort
        self.ABORT = False
        
    
    def endState(self):
        for module in self.modules:
            if hasattr(module, 'stop'):
                module.stop()
        return 
    
    def malloc_snapshot(self):
        # Used for checking for memory leaks
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        print("[ Top 5 ]")
        for stat in top_stats[:5]:
            print(stat)
        
        # if hasattr(self, 'last_snapshot'):
        #     top_stats = snapshot.compare_to(self.last_snapshot, 'lineno')
        #     print('[ Top 5 Differences ]')
        #     for stat in top_stats[:5]:
        #         print(stat)
        print('\n\n\n')
        
        
        # Save snapshot and schedule next one
        self.last_snapshot = snapshot
        self.GUI.root.after(5000, self.malloc_snapshot)
        return
        
        
    
    
            




class GUI():
    
    def __init__(self, root, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        self.root = root
        self.params = {} # master dict to store all parameters
                
        root.title("SECM Controller")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0) 
        root.option_add('*tearOff', FALSE)
        
        
        # Menu bar
        menubar = Menu(root)
        root['menu'] = menubar
        menu_file = Menu(menubar)
        menu_settings = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        menubar.add_cascade(menu=menu_settings, label='Settings')
        
        
        menu_file.add_command(label='New', command=self.newFile)
        menu_file.add_command(label='Open...', command=self.openFile)
        menu_file.add_command(label='Save', command=self.save)
        menu_file.add_command(label='Save as...', command=self.saveAs)
        menu_file.add_command(label='Quit', command=self.Quit)
        
        menu_settings.add_command(label='Save settings...', command=self.save_settings)
        menu_settings.add_command(label='Load settings...', command=self.load_settings)
        
                
        
        leftpanel = Frame(self.root)
        leftpanel.grid(row=1, column=0, sticky=(N, S))
        
        rightpanel = Frame(self.root)
        rightpanel.grid(row=1, column=1)
        
        
        # tabControl = Notebook(leftpanel)
        
        # secm_frame  = Frame(tabControl)
        # pstat_frame = Frame(tabControl)
        
        pstat_frame = Frame(leftpanel)
        pstat_frame.grid(row=0, column=0, sticky=(N,W,E))
        secm_frame = Frame(leftpanel)
        secm_frame.grid(row=1, column=0, sticky=(N,W,E))
        
        
        # tabControl.add(pstat_frame, text ='Potentiostat Control')
        # tabControl.add(secm_frame, text ='SECM Control')
        # tabControl.grid(row=0, column=0, sticky=(N))
           
        ######################################
        #####                            #####
        #####          FIGURES           #####                            
        #####                            #####
        ######################################
        
        # Label(rightpanel, text='right frame').grid(column=1, row=1)
        topfigframe = Frame(rightpanel)
        topfigframe.grid(row=0, column=1)
        topfigframe.pack_propagate(0)
        
        Separator(rightpanel, 
                  orient='horizontal').grid(row=1, column=1, sticky=(W,E))
        
        botfigframe = Frame(rightpanel)
        botfigframe.grid(row=2, column=1)
        botfigframe.pack_propagate(0)
        
        
        self.topfig = plt.Figure(figsize=(3,3), dpi=75)
        self.botfig = plt.Figure(figsize=(3,3), dpi=75)
        
        self.topfig.add_subplot(111)
        self.botfig.add_subplot(111)
        
        
        
        Label(topfigframe, text='Display: ').grid(column=0, row=0, 
                                                  sticky=(W,E))
        heatmapOptions = [
            'Max. current',
            'Current @ ... (V)',
            'Z height',
            'Avg. current'
            ]
        self.heatmapselection = StringVar(topfigframe)
        OptionMenu(topfigframe, self.heatmapselection, 
                   heatmapOptions[0], *heatmapOptions).grid(column=1, 
                                                            row=0, 
                                                            sticky=(W,E))
        self.HeatMapDisplayParam = Text(topfigframe, height=1, width=5)
        self.HeatMapDisplayParam.insert('1.0', '')
        self.HeatMapDisplayParam.grid(column=2, row=0, sticky=(W,E))
        
        FigureCanvasTkAgg(self.topfig, master=topfigframe
                          ).get_tk_widget().grid(
                                              row=1, column=0,
                                              columnspan=10)
        
        
        fig2Options = [
             'V vs t',
             'I vs t',
             'I vs V',
             ]
                              
        Label(botfigframe, text='Show: ').grid(column=0, row=0, sticky=(W,E))
        self.fig2selection = StringVar(botfigframe)
        OptionMenu(botfigframe, self.fig2selection, fig2Options[2], 
                   *fig2Options, command=self.fig_opt_changed).grid(column=1, row=0, sticky=(W,E))
        # option13 = StringVar(botfigframe)
        # OptionMenu(botfigframe, option13, 'Option 3', 
        #            *['Option 3', '']).grid(column=2, row=0, sticky=(W,E))                      
                              
        FigureCanvasTkAgg(self.botfig, master=botfigframe
                          ).get_tk_widget().grid(
                                              row=1, column=0,
                                              columnspan=10)                       
        
        
        
        

        ######################################
        #####                            #####
        #####   POTENTIOSTAT CONTROLS    #####                            
        #####                            #####
        ######################################
        
        
        PSTAT_TABS = Notebook(pstat_frame)
        
        amplifier_control = Frame(PSTAT_TABS)
        cv_control        = Frame(PSTAT_TABS)
        eis_control       = Frame(PSTAT_TABS)
        ca_control        = Frame(PSTAT_TABS)
        
        PSTAT_TABS.add(amplifier_control, text='Amplifier')
        PSTAT_TABS.add(cv_control, text='  CV  ')
        PSTAT_TABS.add(eis_control, text='  EIS  ')
        PSTAT_TABS.add(ca_control, text='  CA  ')
        PSTAT_TABS.pack(expand=1, fill='both')
        
        
        self.params['CV'] = make_CV_window(self, cv_control)
        
        self.amp_param_fields  = make_amp_window(self, amplifier_control)
        self.params['amp']  = {}
        
        ###  TODO: UNCOMMENT ME FOR FINAL CONFIG. STARTUP FROM KNOWN AMP. STATE ###
        # self.set_amplifier()
        ######################
    
    
    
    
    
        ######################################
        #####                            #####
        #####       SECM CONTROLS        ##### 
        #####                            #####
        ######################################
    
    
        SECM_TABS = Notebook(secm_frame)
        
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
        self.params['hopping'] = make_hopping_window(self, hopping_mode)
    
    
        # Initialize plotter
        Plotter(self.master, self.topfig, self.botfig)
    
    
        # Always-running functions
        masterthread    = run(self.master.run)
        readerthread    = run(self.master.HekaReader.read_stream)
    
        self.threads = [masterthread, readerthread]
        return
    #################### END __init__ ##############################
    
        ######################################
        #####                            #####
        #####       CALLBACK FUNCS       #####  
        #####                            #####
        ######################################
    
    ########## GUI CALLBACKS ###########    
    
    # create new measurement file
    def newFile(self):
        pass
    
    # load previous data
    def openFile(self):
        f = filedialog.askopenfilename(initialdir='D:\SECM\Data')
        if not f.endswith('.secmdata'):
            return
        expt = load_from_file(f)
        self.master.set_expt(expt)
        self.master.Plotter.load_from_expt(expt)
        pass
    
    # save current file to disk
    def save(self):
        if self.master.expt:
            if self.master.expt.path == 'temp.secmdata':
                return self.saveAs()
            self.master.expt.save()
    
    # save current file under new path
    def saveAs(self):
        if self.master.expt:
            f = filedialog.asksaveasfilename(
                defaultextension='.secmdata', initialdir='D:\SECM\Data')
            if not f: return
            self.master.expt.save(f)
    
    # Exit program
    def Quit(self):
        self.root.destroy()
    
    
    def save_settings(self):
        settings = {
            'heatmapselection': self.heatmapselection,      # StringVar
            'HeatMapDisplayParam': self.HeatMapDisplayParam, # Text
            'fig2selection': self.fig2selection,            # StringVar
            'params': {
                'CV': self.params['CV'],            # dict
                'amp': self.params['amp'],          # dict
                'hopping': self.params['hopping']   # dict
                },
            }
        
        
        def convert_field(field):
            if isinstance(field, StringVar):
                return field.get()
            elif isinstance(field, Text):
                return field.get('1.0', 'end').rstrip('\n')
            return None
        
        
        def convert_all(d):
            # Recursively iterate through settings dict and sub-dicts
            for key, value in d.items():
                if isinstance(value, dict):
                    d[key] = convert_all(value)
                    continue
                d[key] = convert_field(value)
            return d
        
        settings = convert_all(settings)
        SETTINGS_FILE = filedialog.asksaveasfilename(initialdir='settings/',
                                                     defaultextension='.json')
        if not SETTINGS_FILE: return
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
          
    
    
    def load_settings(self):
        pass
    
    
    # Selected new view for fig2
    def fig_opt_changed(self, _):
        self.master.Plotter.update_fig2data(
            data = self.master.Plotter.data2
            )
    
    
    ########## ELECTROCHEMISTRY CALLBACKS ###########
    
    # Take parameters from CV window and send to HEKA    
    def set_amplifier(self):
        new_params = convert_to_index(self.amp_param_fields)
        self.amp_params = new_params
        cmds = []
        for key, val in new_params.items():
            if key == 'float_gain':
                continue
            if val != self.params['amp'].get(key, None):
                cmds.append(f'{key} {val}')
        
        for cmd in cmds:
            self.master.HekaWriter.macro(cmd)
        
        self.params['amp'] = new_params
        self.master.make_ready()
        return
    
    def get_CV_params(self):
        cv_params = self.params['CV'].copy()
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
            return 0,0,0,0,0,0
        return E0, E1, E2, E3, v, t0
    
    def run_CV(self):
        self.set_amplifier()
        E0, E1, E2, E3, v, t0 = self.get_CV_params()
        if v > 0.1:
            print('max scan rate 100mV/s - gotta fix')
            return
        self.master.HekaWriter.setup_CV(E0, E1, E2, E3, v, t0)
        path = self.master.HekaWriter.run_CV_loop()
        self.master.make_ready()
        return path
    
    
    
    
    ########## SECM SCAN CALLBACKS ###########
    
    def run_approach_curve(self):
        self.set_amplifier()
        
    
    def run_hopping(self):
        func = partial(self.master.FeedbackController.hopping_mode,
                        self.params['hopping'])
        run(func)
        
    
            
                                                        
        
                                                            
                
    







if __name__ == '__main__':
    tracemalloc.start()
    master = MasterModule(TEST_MODE = TEST_MODE)
    reader = HekaReader(master)
    writer = HekaWriter(master)
    adc    = ADC(master)
    piezo  = Piezo(master)
    fbc    = FeedbackController(master) # must be loaded last
    
    root = Tk()
    
    try:
        gui = GUI(root, master)
        
        root.after(1000, master.Plotter.update_figs)
        # root.after(1000, master.malloc_snapshot)
        root.mainloop()
        root.quit()
        gui.willStop = True
    except Exception as e:
        print(traceback.format_exc())
    
    if not master.TEST_MODE:
        adc.stop()
        print('stopped ADC')
    
    