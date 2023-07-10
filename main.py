from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, messagebox
import time
import traceback
import tracemalloc
import json
import sys
import os
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
from modules.Picomotor import PicoMotor
from utils.utils import run, Logger
from gui import *

default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr

matplotlib.use('TkAgg')
plt.style.use('secm.mplstyle')

TEST_MODE = False


    
'''
TODO:
    
    - handle forward/backwards CV scans in current @ view
    
    - Make FeedbackController threadsafe
        
    - check on opening new file procedure (might overwrite/ not save)
    
    - steamline echem running process    
        
    Write documentation
        
    HEKA control
    - choose EIS sample rate based on max freq.
    - run multiple echem experiments at each location
    
    

Bugs:
    - Sometimes doesn't send run CV command to PATCHMASTER
    - SerialTimeOut for xyz piezo communications
    - Position tracking doesn't restart on abort
    - Weird behavior running/ saving HEKA data. Possibly if aborting halfway through
    or when saving on new file and changing target
    - Running approach curve when PATCHMASTER isn't open raises an error
    because master.GUI.amp_params doesn't have key 'float_gain'
    
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
        self.ABORT = True
        self.PicoMotor.halt()
        if not self.STOP:
            # Reset
            run(self.make_ready)
    
    
    def make_ready(self):
        time.sleep(2) # wait for other threads to abort
        self.ABORT = False
        # Manual restarts
        self.Piezo.start_monitoring()
        
    
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
        menubar         = Menu(root)
        root['menu']    = menubar
        menu_file       = Menu(menubar)
        menu_settings   = Menu(menubar)
        menu_heatmap    = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        menubar.add_cascade(menu=menu_settings, label='Settings')
        menubar.add_cascade(menu=menu_heatmap, label='Heatmap')
        
        
        menu_file.add_command(label='New', command=self.newFile)
        menu_file.add_command(label='Open...', command=self.openFile)
        menu_file.add_command(label='Save', command=self.save)
        menu_file.add_command(label='Save as...', command=self.saveAs)
        menu_file.add_command(label='Export...', command=self.export)
        menu_file.add_command(label='Quit', command=self.Quit)
        
        menu_settings.add_command(label='Save settings...', command=self.save_settings)
        menu_settings.add_command(label='Load settings...', command=self.load_settings)
        
        menu_heatmap.add_command(label='Set scale...', command=self.set_heatmap_scale)
        menu_heatmap.add_command(label='Set colors...', command=self.set_heatmap_colors)
        menu_heatmap.add_command(label='Line scan', command=self.heatmap_line_scan)
        
        
                
        # Left panel: potentiostat/ SECM parameters
        leftpanel = Frame(self.root)
        leftpanel.grid(row=1, column=0, sticky=(N, S))
        
        # Right panel: Figures
        rightpanel = Frame(self.root)
        rightpanel.grid(row=1, column=1)
        
        # Bottom panel: Console
        bottompanel = Frame(self.root)
        bottompanel.grid(row=2, column=0, columnspan=2, sticky=(N,W,E))
        console = Text(bottompanel, width=125, height=10)
        console.grid(row=0, column=0, sticky=(N,S,E,W))
        pl = PrintLogger(console)
        sys.stdout = pl
        
        
        abortbuttonframe = Frame(leftpanel)
        abortbuttonframe.grid(row=0, column=0)
        Button(abortbuttonframe, text='Stop', command=self.master.abort,
               width=50).grid(row=0, column=0, sticky=(W,E))
        
        pstat_frame = Frame(leftpanel)
        pstat_frame.grid(row=1, column=0, sticky=(N,S,W,E))
        secm_frame = Frame(leftpanel)
        secm_frame.grid(row=2, column=0, sticky=(N,S,W,E))
        piezo_frame = Frame(leftpanel)
        piezo_frame.grid(row=3, column=0, sticky=(N,S,W,E))
        
                   
        ######################################
        #####                            #####
        #####          FIGURES           #####                            
        #####                            #####
        ######################################
        
        # Label(rightpanel, text='right frame').grid(column=1, row=1)
        topfigframe = Frame(rightpanel)
        topfigframe.grid(row=0, column=0)
        
        Separator(rightpanel, 
                  orient='vertical').grid(row=0, column=1, sticky=(N,S))
        
        botfigframe = Frame(rightpanel)
        botfigframe.grid(row=0, column=2)
        
        self.topfig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        self.botfig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        
        self.topfig.add_subplot(111)
        self.botfig.add_subplot(111)
        
        
        
        
        ###############################
        ### HEATMAP DISPLAY OPTIONS ###
        ###############################
        
        Label(topfigframe, text='SECM').grid(column=0, row=0, 
                                                  sticky=(W,E))
        
        Label(topfigframe, text='Display:').grid(column=2, row=0,
                                                 sticky=(W,E))
        
        heatmapOptions = [
            'Max. current',
            'Current @ ... (V)',
            'Current @ ... (t)',
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
        self.params['EIS'] = make_EIS_window(self, eis_control)
        make_CA_window(self, ca_control)
        
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
        custom_scan    = Frame(SECM_TABS)
        
        SECM_TABS.add(approach_curve, text=' Approach Curve ')
        SECM_TABS.add(hopping_mode, text=' Hopping ')
        SECM_TABS.add(const_current, text=' Constant I ')
        SECM_TABS.add(const_height, text=' Constant Z ')
        SECM_TABS.pack(expand=1, fill='both')
        SECM_TABS.select(approach_curve)
        
        
        self.params['approach'] = make_approach_window(self, approach_curve)
        self.params['hopping']  = make_hopping_window(self, hopping_mode)
        
        
        ######################################
        #####                            #####
        #####      PIEZO CONTROLS        ##### 
        #####                            #####
        ######################################
        
        PIEZO_TABS = Notebook(piezo_frame)
        piezo_control = Frame(PIEZO_TABS)
        z_piezo_control = Frame(PIEZO_TABS)
        piezo_control.grid(row=0, column=0, sticky=(W,E))
        
        self._x_display = StringVar()
        self._y_display = StringVar()
        self._z_display = StringVar()
        
        self._x_set = StringVar(value='0')
        self._y_set = StringVar(value='0')
        self._z_set = StringVar(value='0')
        
        self._piezo_msg = StringVar()
        
        Label(piezo_control, text='  X:').grid(row=0, column=0, sticky=(W,E))
        Label(piezo_control, textvariable=self._x_display).grid(row=0, column=1, sticky=(W,E))
        Label(piezo_control, text='  Y:').grid(row=0, column=2, sticky=(W,E))
        Label(piezo_control, textvariable=self._y_display).grid(row=0, column=3, sticky=(W,E))
        Label(piezo_control, text='  Z:').grid(row=0, column=4, sticky=(W,E))
        Label(piezo_control, textvariable=self._z_display).grid(row=0, column=5, sticky=(W,E))
        
        Entry(piezo_control, textvariable=self._x_set, width=6).grid(row=1, column=0, columnspan=2, sticky=(W,E))
        Entry(piezo_control, textvariable=self._y_set, width=6).grid(row=1, column=2, columnspan=2, sticky=(W,E))
        Entry(piezo_control, textvariable=self._z_set, width=6).grid(row=1, column=4, columnspan=2, sticky=(W,E))
        Button(piezo_control, text='Set', command=self.piezo_goto).grid(row=1, column=6, sticky=(W,E))
        
        Entry(piezo_control, textvariable=self._piezo_msg, width=20).grid(row=2, column=0, columnspan=6, sticky=(W,E))
        Button(piezo_control, text='Send Cmd', command=self.piezo_msg_send).grid(row=2, column=6, sticky=(W,E))
        
        
        self._piezosteps = StringVar(value='0')
        
        Label(z_piezo_control, text='Steps:').grid(row=0, column=0, sticky=(W,E))
        Entry(z_piezo_control, textvariable=self._piezosteps, width=8).grid(row=0, column=1, sticky=(W,E))
        Button(z_piezo_control, text='Go', command=self.z_piezo_go).grid(row=0, column=2, sticky=(W,E))
        Label(z_piezo_control, text='(1 step = ~30 nm)').grid(row=0, column=3, sticky=(W))
        Button(z_piezo_control, text='Stop', command=self.z_piezo_stop).grid(row=1, column=2, sticky=(W,E))
        
        
        PIEZO_TABS.add(piezo_control, text='Piezo')
        PIEZO_TABS.add(z_piezo_control, text='Z Positioner')
        PIEZO_TABS.pack(expand=1, fill='both')
        
        
    
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
                'hopping': self.params['hopping'],  # dict
                'approach': self.params['approach']
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
    
    
    def _update_piezo_display(self):
        self._x_display.set(f'{self.master.Piezo.x:0.3f}')
        self._y_display.set(f'{self.master.Piezo.y:0.3f}')
        self._z_display.set(f'{self.master.Piezo.z:0.3f}')
        self.root.after(250, self._update_piezo_display)
        
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
            
    # export current file to folder of CSV's for each data point
    def export(self):
        if self.master.expt:
            f = filedialog.askdirectory(
                title='Select folder to save to',
                initialdir='D:\SECM\Data', mustexist=False)
            if not f: return
            
            if os.path.exists(f):
                if len(os.listdir(f)) > 0:
                    confirm = messagebox.askyesno('Save to existing folder?',
                              'Warning! Folder already exists and is not empty. Data in folder may be overwritten. Continue saving?')
                    if not confirm:
                        return
            
            self.master.expt.save_to_folder(f)
            
    
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
        
     
    ########## DISPLAY FIGURE CALLBACKS ###########
    
    # Selected new view for fig2
    def fig_opt_changed(self, _):
        # self.master.Plotter.update_fig2data(
        #     data = self.master.Plotter.data2
        #     )
        self.master.Plotter.set_echemdata(
            DATAPOINT = self.master.Plotter.fig2data 
            )
        return
    
    
    def heatmap_opt_changed(self, *args):
        # selected a new view for heatmap
        option = self.heatmapselection.get()
        value  = self.HeatMapDisplayParam.get('1.0', 'end')
        
        self.master.Plotter.update_heatmap(option, value)        
        return
    
    
    
    def heatmap_rect_zoom(self):
        self.master.Plotter.heatmap_zoom()
    
    
    def heatmap_line_scan(self):
        self.master.Plotter.heatmap_line_scan()
        
    
    def set_heatmap_scale(self):
        '''
        Open popup for user to adjust max/min value and colormap for heatmap
        '''
        self.master.Plotter.heatmap_scale_popup()
        
        
    def set_heatmap_colors(self):
        '''
        Open popup for user to set the color map
        '''
        self.master.Plotter.heatmap_color_popup()
        
    
    
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
            # if val != self.amp_params.get(key, None):
            cmds.append(f'Set {key} {val}')
        
        self.master.HekaWriter.send_multiple_cmds(cmds)
        
        self.amp_params = new_params # Store current amplifier state to amp_params
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
        path = self.master.HekaWriter.run_measurement_loop('CV')
        self.master.make_ready()
        return path
    
    
    def get_EIS_params(self):
        eis_params = self.params['EIS'].copy()
        E0      = eis_params['E0'].get('1.0', 'end')
        f0      = eis_params['f0'].get('1.0', 'end')
        f1      = eis_params['f1'].get('1.0', 'end')
        n_pts   = eis_params['n_pts'].get('1.0', 'end')
        amp     = eis_params['amp'].get('1.0', 'end')
        vals = [E0, f0, f1, n_pts, amp]
        try:
            E0, f0, f1, n_pts, amp = [float(val) for val in vals]
            n_pts = int(n_pts)
        except:
            print('invalid EIS inputs')
            return 0,0,0,0,0
        return E0, f0, f1, n_pts, amp
    
    def run_EIS(self):
        # TODO: implement EIS
        # validate EIS parameters
        # generate waveform
        # check saved waveform
        # write waveform file
        # send command to HEKA
        eis_params = self.get_EIS_params()
        self.master.HekaWriter.setup_EIS(*eis_params)
        path = self.master.HekaWriter.run_measurement_loop('EIS')
        self.master.make_ready()
        return
    
    
    
    
    ########## SECM SCAN CALLBACKS ###########
    
    def run_approach_curve(self):
        self.set_amplifier()
        
        height = self.params['approach']['z_height'].get('1.0', 'end')
        height  = float(height)

        func = partial(self.master.FeedbackController.approach,
                       height)
        run(func)
    
    
    def run_retract(self):
        func = partial(self.master.Piezo.retract, 10, True)
        run(func)
    
        
    def run_automatic_approach(self):
        self.set_amplifier()
        run(self.master.FeedbackController.automatic_approach)
        
    
    def run_hopping(self):
        self.set_amplifier()
        func = partial(self.master.FeedbackController.hopping_mode,
                        self.params['hopping'])
        run(func)
        
    
            
                                                        
     ########## PIEZO CALLBACKS ###########   
                                                            
    def piezo_goto(self):
        x = self._x_set.get()
        y = self._y_set.get()
        z = self._z_set.get()
        
        def validate(n):
            try:
                n = float(n)
            except:
                print(f'Input error: {n}')
                return None
            if (n >= 0 and n <= 80):
                return float(n)
            print(f'Input out of range [0, 80]: {n}')
            return None
        
        x = validate(x)
        y = validate(y)
        z = validate(z)
        
        if any(var is None for var in (x,y,z)):
            return
        
        self.master.Piezo.goto(x, y, z)
        return
    
    
    def piezo_msg_send(self):
        msg = self._piezo_msg.get()
        self.master.Piezo.write_and_read(msg)
        
    
    def z_piezo_go(self):
        steps = self._piezosteps.get()
        try:
            steps = int(steps)
        except:
            print(f'Invalid input:"{steps}"')
            return
        self.master.PicoMotor.step(steps)
        return
    
    
    def z_piezo_stop(self):
        self.master.PicoMotor.halt()
        return
        
            
    







if __name__ == '__main__':
    tracemalloc.start()
    master = MasterModule(TEST_MODE = TEST_MODE)
    reader = HekaReader(master)
    writer = HekaWriter(master)
    adc    = ADC(master)
    piezo  = Piezo(master)
    motor  = PicoMotor(master)
    fbc    = FeedbackController(master) # must be loaded last
    
    root = Tk()
    
    try:
        gui = GUI(root, master)
        
        gui._update_piezo_display()
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
        sys.stdout = default_stdout
        sys.stdin  = default_stdin
        sys.stderr = default_stderr
        print(traceback.format_exc())

    if not master.TEST_MODE:
        adc.stop()
        piezo.stop()
        motor.stop()
    
    sys.stdout = default_stdout
    sys.stdin  = default_stdin
    sys.stderr = default_stderr
    
    
    
    