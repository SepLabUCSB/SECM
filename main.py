from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, messagebox
import time
import traceback
import tracemalloc
import json
import sys
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
from utils.utils import run, Logger
import gui
from gui import *

default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr

matplotlib.use('TkAgg')
plt.style.use('default')

TEST_MODE = True


    
'''
TODO:
    
    Lock thread - i.e. make only one button call an object at a time
         
    Make separate data viewer to make high quality figures
    
    Write documentation
        
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
    
    DISPLAY
    - Color by average value
    - Color by value at ...
    - Color by...
    - 
    
    
    
'''

global gl_st 
gl_st = time.time()

SETTINGS_FILE = 'settings/DEFAULT.json'

class MasterModule(Logger):
    '''
    MasterModule controlls all submodules and lets them communicate with each other.
    
    When a new module is initiated, it should must be passed a reference to 
    MasterModule. The submodule sets self.master and passes itself to 
    master.register(). Then, the submodule can be accessed by master or any
    other module as master.submodule    
    
    Master also stores the current experiment and the global ABORT flag.
    Submodules should check for master.ABORT to break out of loops.
   
    '''
    def __init__(self, TEST_MODE):
        # TEST_MODE: bool, True = record fake data
        self.willStop   = False
        self.STOP       = False
        self.ABORT      = False
        self.TEST_MODE  = TEST_MODE
        
        self.modules    = [self]
        
        self.expt = Experiment()
        self.log('')
        self.log('')
        self.log('========= Master Initialized =========')
        
        
    def register(self, module):
        # register a submodule to master
        setattr(self, module.__class__.__name__, module)
        self.modules.append(getattr(self, module.__class__.__name__))
        self.log(f'Loaded {module.__class__.__name__}')
    
    
    def set_expt(self, expt):
        self.check_save()
        self.expt = expt
    
    
    def check_save(self):
        if not self.expt.isSaved():
            self.GUI.savePrevious()
    
    
    def run(self):
        '''
        Master main loop
        !! Runs in its own thread !!
        Checks if any module has issued a global stop command.
        If so, stops all other modules.
        '''
        while True:
            for module in self.modules:
                if module.willStop:
                    # STOP flag stops everything
                    self.STOP = True
                    self.abort()
                    self.log('Stopping')
                    self.check_save()
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
        
        
 
    
class PrintLogger(): 
    '''
    File like object to print console output into Tkinter window
    set sys.stdout = PrintLogger, then print() will print to
    PrintLogger.textbox
    '''
    def __init__(self, textbox): 
        self.textbox = textbox # tk.Text object

    def write(self, text):
        self.textbox.insert(END, text) # write text to textbox
        self.textbox.see('end') # scroll to end

    def flush(self): # needed for file like object
        pass
    



class GUI(Logger):
    '''
    Graphical user interface
    '''
    
    def __init__(self, root, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.root = root
        self.params = {} # master dict to store all parameters
        self.amp_params = {} # stores current state of amplifier
                
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
        
                
        # Left panel: potentiostat/ SECM parameters
        leftpanel = Frame(self.root)
        leftpanel.grid(row=1, column=0, sticky=(N, S))
        
        # Right panel: Figures
        rightpanel = Frame(self.root)
        rightpanel.grid(row=1, column=1)
        
        # Bottom panel: Console
        bottompanel = Frame(self.root)
        bottompanel.grid(row=2, column=0, columnspan=2, sticky=(N,W,E))
        console = Text(bottompanel, width=70, height=10)
        console.grid(row=0, column=0, sticky=(N,S,E,W))
        pl = PrintLogger(console)
        sys.stdout = pl
        
        
        # tabControl = Notebook(leftpanel)
        
        # secm_frame  = Frame(tabControl)
        # pstat_frame = Frame(tabControl)
        
        pstat_frame = Frame(leftpanel)
        pstat_frame.grid(row=0, column=0, sticky=(N,S,W,E))
        secm_frame = Frame(leftpanel)
        secm_frame.grid(row=1, column=0, sticky=(N,S,W,E))
        
        
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
        topfigframe.grid(row=0, column=0)
        topfigframe.pack_propagate(0)
        
        Separator(rightpanel, 
                  orient='vertical').grid(row=0, column=1, sticky=(N,S))
        
        botfigframe = Frame(rightpanel)
        botfigframe.grid(row=0, column=2)
        botfigframe.pack_propagate(0)
        
        
        self.topfig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        self.botfig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        
        self.topfig.add_subplot(111)
        self.botfig.add_subplot(111)
        
        
        
        
        ###############################
        ### HEATMAP DISPLAY OPTIONS ###
        ###############################
        
        Label(topfigframe, text='SECM').grid(column=0, row=0, 
                                                  sticky=(W,E))
        heatmapOptions = [
            'Max. current',
            'Current @ ... (V)',
            'Z height',
            'Avg. current'
            ]
        self.heatmapselection = StringVar(topfigframe)
        OptionMenu(topfigframe, self.heatmapselection, 
                   heatmapOptions[0], *heatmapOptions).grid(column=2, 
                                                            row=1, 
                                                            sticky=(W,E))
        self.heatmapselection.trace('w', self.heatmap_opt_changed)
        
        self.HeatMapDisplayParam = Text(topfigframe, height=1, width=5)
        self.HeatMapDisplayParam.insert('1.0', '')
        self.HeatMapDisplayParam.grid(column=3, row=1, sticky=(W,E))
        
        Button(topfigframe, text='Zoom to grid...', 
               command=self.heatmap_rect_zoom).grid(column=0, row=1,
                                                    sticky=(W,E))
        Button(topfigframe, text='Set new area',
               command=self.set_new_area).grid(column=1, row=1,
                                               sticky=(W,E))
        
        FigureCanvasTkAgg(self.topfig, master=topfigframe
                          ).get_tk_widget().grid(
                                              row=2, column=0,
                                              columnspan=10)
        
        
        ##################    
        #### FIGURE 2 ####
        ##################    
                 
        fig2Options = [
             'V vs t',
             'I vs t',
             'I vs V',
             ]
        Label(botfigframe, text='Electrochemistry').grid(column=0, row=0)
        # Label(botfigframe, text='Show: ').grid(column=0, row=1, sticky=(W,E))
        self.fig2selection = StringVar(botfigframe)
        OptionMenu(botfigframe, self.fig2selection, fig2Options[2], 
                   *fig2Options, command=self.fig_opt_changed).grid(column=0, row=1, sticky=(W,E))
        # option13 = StringVar(botfigframe)
        # OptionMenu(botfigframe, option13, 'Option 3', 
        #            *['Option 3', '']).grid(column=2, row=0, sticky=(W,E))                      
                              
        FigureCanvasTkAgg(self.botfig, master=botfigframe
                          ).get_tk_widget().grid(
                                              row=2, column=0,
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
        self.params['amp'] = make_amp_window(self, amplifier_control)
        
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
        SECM_TABS.select(hopping_mode)
        
        
        make_approach_window(self, approach_curve)
        self.params['hopping'] = make_hopping_window(self, hopping_mode)
    
    
        # Initialize plotter
        Plotter(self.master, self.topfig, self.botfig)
        
        
        # Collect all settings for saving/ loading
        self.__settings = {
            'heatmapselection': self.heatmapselection,      # StringVar
            'HeatMapDisplayParam': self.HeatMapDisplayParam, # Text
            'fig2selection': self.fig2selection,            # StringVar
            'params': {
                'CV': self.params['CV'],            # dict
                'amp': self.params['amp'],          # dict
                'hopping': self.params['hopping']   # dict
                },
            }
    
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
    
    def savePrevious(self):
        if self.master.TEST_MODE: return
        answer = messagebox.askyesno('Save previous?', 
                          'Do you want to save the unsaved data?')
        if not answer:
            return
        self.saveAs()
                          
    
    # Exit program
    def Quit(self):
        self.root.destroy()
    
    
    def save_settings(self):

        def convert_field(field):
            if isinstance(field, StringVar):
                return field.get()
            elif isinstance(field, Text):
                return field.get('1.0', 'end').rstrip('\n')
            return None

        def convert_all(d):
            # Recursively iterate through settings dict and sub-dicts
            d2 = dict() # Copy everything to a new output dict to avoid
                        # modifying self.__settings
            for key, value in d.items():
                if isinstance(value, dict):
                    d2[key] = convert_all(value)
                    continue
                d2[key] = convert_field(value)
            return d2
        
        settings = convert_all(self.__settings)
        SETTINGS_FILE = filedialog.asksaveasfilename(initialdir='settings/',
                                                     defaultextension='.json')
        if not SETTINGS_FILE: return
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
        
        return
          
    
    
    def load_settings(self):
        SETTINGS_FILE = filedialog.askopenfilename(initialdir='settings/')
        if not SETTINGS_FILE: return
        with open(SETTINGS_FILE, 'r') as f:
            loaded = json.load(f)
        
        
        def set_value(field, value):
            if isinstance(field, StringVar):
                field.set(value)
            if isinstance(field, Text):
                field.delete('1.0', 'end')
                field.insert('1.0', value)

        def set_all(settings_dict, loaded_dict):
            # Recursively iterate through settings dict and sub-dicts
            for key, field, value in zip(settings_dict.keys(), 
                                         settings_dict.values(),
                                         loaded_dict.values()):
                if isinstance(value, dict):
                    settings_dict[key] = set_all(settings_dict[key], value)
                    continue
                set_value(settings_dict[key], value)
            return settings_dict
        
        set_all(self.__settings, loaded)
        
        return
        
     
    
    
    # Selected new view for fig2
    def fig_opt_changed(self, _):
        self.master.Plotter.update_fig2data(
            data = self.master.Plotter.data2
            )
    
    
    def heatmap_opt_changed(self, *args):
        # selected a new view for heatmap
        option = self.heatmapselection.get()
        value  = self.HeatMapDisplayParam.get('1.0', 'end')
        
        self.master.Plotter.update_heatmap(option, value)        
        return
    
    
    
    def heatmap_rect_zoom(self):
        self.master.Plotter.heatmap_zoom()
    
    def set_new_area(self):
        corners = self.master.Plotter.RectangleSelector.get_coords()
        if all([c == (0,0) for c in corners]):
            return
        scale = self.master.Piezo.set_new_scan_bounds(corners)
        gui.params['hopping']['size'].delete('1.0', 'end')
        gui.params['hopping']['size'].insert('1.0', f"{scale:0.3f}")
        return
    
    
    ########## ELECTROCHEMISTRY CALLBACKS ###########
    
    # Take parameters from CV window and send to HEKA    
    def set_amplifier(self):
        if not self.master.HekaReader.PatchmasterRunning():
            self.log('PATCHMASTER not opened!')
            return
        new_params = convert_to_index(self.params['amp'])
        cmds = []
        for key, val in new_params.items():
            if key == 'float_gain':
                continue
            if val != self.amp_params.get(key, None):
                cmds.append(f'Set {key} {val}')
        
        # for cmd in cmds:
        #     self.master.HekaWriter.send_command(cmd)
        self.master.HekaWriter.send_multiple_cmds(cmds)
        
        self.amp_params = new_params # Store current amplifier state to amp_params
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
        
        sys.stdout = default_stdout
        sys.stdin  = default_stdin
        sys.stderr = default_stderr
        
    except Exception as e:
        # Catch exceptions to make sure adc port closes and 
        # stdout resets to default
        print(traceback.format_exc())

    if not master.TEST_MODE:
        adc.stop()
    
    
    sys.stdout = default_stdout
    sys.stdin  = default_stdin
    sys.stderr = default_stderr
    
    
    