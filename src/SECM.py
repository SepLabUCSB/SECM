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
from .modules.HekaIO import HekaReader, HekaWriter
from .modules.ADC import ADC
from .modules.Piezo import Piezo
from .modules.FeedbackController import FeedbackController, make_datapoint_from_file, load_echem_from_file
from .modules.Plotter import Plotter, ExporterGenerator
from .modules.DataStorage import Experiment, EISDataPoint, load_from_file
from .modules.Picomotor import PicoMotor
from .modules.ImageCorrelator import ImageCorrelator
from .utils.utils import run, Logger, focus_next_widget
from .gui import *
from .gui.hopping_popup import HoppingPopup

default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr

matplotlib.use('TkAgg')

TEST_MODE = False


    
'''
TODO:
    - image exporting
    
    - Bode plot options
            
    - check on opening new file procedure (might overwrite/ not save)
    
        
    Write documentation
        
    HEKA control
    - choose EIS sample rate based on max freq.
    
    

Bugs:
    - Starting hopping mode scan doesn't go to correct spot??
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

plt_style_dict = {
    'figure.figsize': (5, 5),
    'figure.dpi': 300,
    'font.family': 'Calibri',
    'font.size': 20,
    'mathtext.default': 'regular',
    'axes.linewidth': 2,
    'axes.labelpad': 10,
    'axes.spines.right': False,
    'axes.spines.top': False,
    'axes.prop_cycle': matplotlib.cycler('color', 
                                         ['4C72B0', '55A868', 
                                          'C44E52', '8172B2', 
                                          'CCB974', '64B5CD']),
    'xtick.top': False,
    'xtick.direction': 'out',
    'xtick.major.size': 7,
    'xtick.major.width': 2,
    'xtick.minor.size': 5,
    'xtick.minor.width': 2,
    'ytick.right': False,
    'ytick.direction': 'out',
    'ytick.major.size': 7,
    'ytick.major.width': 2,
    'ytick.minor.size': 5,
    'ytick.minor.width': 2,
    'lines.linewidth': 2.5,
    'lines.solid_capstyle': 'round',
    'legend.framealpha': 1,
    'legend.frameon': False
    }
plt.style.use(plt_style_dict)

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
    
    
    def set_expt(self, expt, name=None):
        self.check_save()
        self.expt = expt
        title = name if name else 'SECM Controller'
        self.GUI.root.title(title)
            
    
    
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
        self.textbox.tag_config("red", foreground="red")
        self.textbox.tag_config('black', foreground='black')

    def write(self, text):
        self.textbox.configure(state='normal')
        color='black'
        for msg in ('Warning', 'warning', 'Error', 'error'):
            if msg in text:
                color='red'
        if 'Found surface' in text:
            color='blue'
        if 'Finished running' in text:
            color='green'
        self.textbox.insert(END, text, color) # write text to textbox
        self.textbox.see('end') # scroll to end
        self.textbox.configure(state='disabled')

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
        menu_analysis   = Menu(menubar)
        menu_image      = Menu(menubar)
        menu_image_corr = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        menubar.add_cascade(menu=menu_settings, label='Settings')
        menubar.add_cascade(menu=menu_analysis, label='Analysis')
        menubar.add_cascade(menu=menu_image, label='Image')
        menubar.add_cascade(menu=menu_image_corr, label='SEM Correlation')
        
        
        menu_file.add_command(label='New', command=self.newFile)
        menu_file.add_command(label='Open...', command=self.openFile)
        menu_file.add_command(label='Open Echem...', command=self.openEchemFile)
        menu_file.add_command(label='Save', command=self.save)
        menu_file.add_command(label='Save as...', command=self.saveAs)
        menu_file.add_command(label='Export...', command=self.export)
        menu_file.add_command(label='Quit', command=self.Quit)
        
        menu_settings.add_command(label='Save settings...', command=self.save_settings)
        menu_settings.add_command(label='Load settings...', command=self.load_settings)
        
        menu_analysis.add_command(label='Set analysis function...', command=self.set_analysis_func)
        
        menu_image.add_command(label='Export heatmap...', command=self.export_heatmap)
        menu_image.add_command(label='Export echem figure...', command=self.export_echem_fig)
        menu_image.add_command(label='Export heatmap data...', command=self.export_heatmap_data)
        menu_image.add_command(label='Export echem data...', command=self.export_echem_fig_data)
        
        menu_image_corr.add_command(label='Load SEM image...', command=self.load_SEM_image)
        
                
        # Left panel: potentiostat/ SECM parameters
        leftpanel = Frame(self.root)
        leftpanel.grid(row=1, column=0, sticky=(N,S,W,E))
        
        # Right panel: Figures
        rightpanel = Frame(self.root)
        rightpanel.grid(row=1, column=1, sticky=(N,S,W,E))
        
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
        
        timeestframe = Frame(leftpanel)
        timeestframe.grid(row=1, column=0)
        Label(timeestframe, text='Estimated time remaining: ').grid(
            row=0, column=0, sticky=(W))
        self._time_est = StringVar()
        Label(timeestframe, textvariable=self._time_est, width=20).grid(
            row=0, column=1, sticky=(W), columnspan=2)
        
        pstat_frame = Frame(leftpanel)
        pstat_frame.grid(row=2, column=0, sticky=(N,S,W,E))
        secm_frame = Frame(leftpanel)
        secm_frame.grid(row=3, column=0, sticky=(N,S,W,E))
        piezo_frame = Frame(leftpanel)
        piezo_frame.grid(row=4, column=0, sticky=(N,S,W,E))
        
                   
        ######################################
        #####                            #####
        #####          FIGURES           #####                            
        #####                            #####
        ######################################
        
        ## Figures ##
        topfigframe = Frame(rightpanel)
        topfigframe.grid(row=0, column=0)
        
        Separator(rightpanel,orient='vertical').grid(
            row=0, column=1, padx=5, sticky=(N,S))
        
        botfigframe = Frame(rightpanel)
        botfigframe.grid(row=0, column=2)
        
        self.topfig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        self.botfig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        
        self.topfig.add_subplot(111)
        self.botfig.add_subplot(111)
        
        Separator(rightpanel, orient='horizontal').grid(
            row=1, column=0, columnspan=10, pady=5, sticky=(W,E))
        
        
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
            'Avg. current',
            'Analysis func.'
            ]
        self.heatmapselection = StringVar(topfigframe)
        OptionMenu(topfigframe, self.heatmapselection, 
                   heatmapOptions[0], *heatmapOptions).grid(column=2, 
                                                            row=1, 
                                                            sticky=(W,E))
        self.heatmapselection.trace('w', self.heatmap_opt_changed)
        
        # self.HeatMapDisplayParam = Text(topfigframe, height=1, width=8)
        # self.HeatMapDisplayParam.insert('1.0', '')
        # self.HeatMapDisplayParam.grid(column=3, row=1, sticky=(W,E))
        # self.HeatMapDisplayParam.bind('<Return>', self.heatmap_opt_changed)
        
        self.HeatMapDisplayParam = StringVar()
        heatmapentry = Entry(topfigframe, width=8, textvariable=self.HeatMapDisplayParam)
        heatmapentry.grid(row=1, column=3, sticky=(W,E))
        heatmapentry.bind('<Return>', self.heatmap_opt_changed)
        
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
                 
        fig2Options = ['V vs t','I vs t','I vs V',]
        EIS_options = ['Nyquist', '|Z| Bode', 'Phase Bode']
        Label(botfigframe, text='Electrochemistry').grid(column=0, row=0)
        
        # Voltammetry view options
        self.fig2selection = StringVar(botfigframe)
        self.fig2typeoptmenu = OptionMenu(botfigframe, self.fig2selection, fig2Options[2], 
                   *fig2Options, command=self.fig_opt_changed)
        self.fig2typeoptmenu.grid(column=0, row=1, sticky=(W,E))
        
        # PointsList selection options
        self.fig2ptselection = IntVar(botfigframe)
        self.fig2ptoptmenu = OptionMenu(botfigframe, self.fig2ptselection, 0, 
                    *[0,], command=self.fig_opt_changed)
        self.fig2ptoptmenu.grid(column=1, row=1, sticky=(W,E))                      
        
        # EIS view options
        self.EIS_view_selection = StringVar()    
        OptionMenu(botfigframe, self.EIS_view_selection, EIS_options[0],
                   *EIS_options, command=self.fig_opt_changed).grid(
                       column=2, row=1, sticky=(W,E))
                       
        FigureCanvasTkAgg(self.botfig, master=botfigframe
                          ).get_tk_widget().grid(
                                              row=2, column=0,
                                              columnspan=10)        
         
        # Initialize plotter
        Plotter(self.master, self.topfig, self.botfig)
        
                              
        ###############################    
        #### HEATMAP IMAGE OPTIONS ####
        ###############################
        
        bottom_menu_frame = Frame(rightpanel)
        bottom_menu_frame.grid(row=2, column=0, sticky=(N,W,S,E))
        
        HEATMAP_TABS = Notebook(bottom_menu_frame)
    
        heatmapscaleframe = Frame(HEATMAP_TABS)
        heatmapcolorframe = Frame(HEATMAP_TABS)
               
        ### Scaling ###
        heatmapscaleframe.grid(row=2, column=0)
        self.heatmap_min_val = StringVar(value='0')
        self.heatmap_max_val = StringVar(value='0')
        Button(heatmapscaleframe, text='Zoom out', 
               command=self.master.Plotter.zoom_out).grid(
               row=1, column=2, sticky=(W,E))
        Button(heatmapscaleframe, text='Zoom in', 
               command=self.master.Plotter.zoom_in).grid(
               row=1, column=3, sticky=(W,E))
        
        Button(heatmapscaleframe, text='-', width=1,
               command=self.master.Plotter.zoom_lower_subt).grid(
               row=2, column=0, sticky=(W,E))  
        Button(heatmapscaleframe, text='+', width=1,
               command=self.master.Plotter.zoom_lower_add).grid(
               row=2, column=1, sticky=(W,E))         
        _min_entry = Entry(heatmapscaleframe, textvariable=self.heatmap_min_val, width=5)
        _min_entry.grid(row=2, column=2, sticky=(W,E))
        _min_entry.bind('<Tab>', focus_next_widget)
        _min_entry.bind('<Return>', self.master.Plotter.apply_minmax_fields)
        
        _max_entry = Entry(heatmapscaleframe, textvariable=self.heatmap_max_val, width=5)
        _max_entry.grid(row=2, column=3, sticky=(W,E))
        _max_entry.bind('<Tab>', focus_next_widget)
        _max_entry.bind('<Return>', self.master.Plotter.apply_minmax_fields)
        Button(heatmapscaleframe, text='-', width=1,
               command=self.master.Plotter.zoom_upper_subt).grid(
               row=2, column=4)
        Button(heatmapscaleframe, text='+', width=1,
               command=self.master.Plotter.zoom_upper_add).grid(
               row=2, column=5)
        
        
        Button(heatmapscaleframe, text='Apply', 
               command=self.master.Plotter.apply_minmax_fields).grid(
               row=3, column=2, sticky=(W,E))
        Button(heatmapscaleframe, text='Reset', 
               command=self.master.Plotter.cancel_popup).grid(
               row=3, column=3, sticky=(W,E))
                   
                   
        ### Color map ###
        cmaps = ['viridis', 'hot', 'gist_gray', 'afmhot', 'plasma', 'inferno', 
                 'magma', 'cividis','Greys', 'Purples', 'Blues', 'Greens', 
                 'Oranges', 'Reds', 'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 
                 'BuPu','GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn',
                 'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu', 'RdYlBu',
                 'RdYlGn', 'coolwarm', 'bwr']
        
        
        self.heatmap_cmap = StringVar()
        OptionMenu(heatmapcolorframe, self.heatmap_cmap, cmaps[0], *cmaps, 
                   command=self.master.Plotter.update_cmap).grid(
                       row=0, column=1, columnspan=2)
        
        self.heatmap_cmap_minval = StringVar(value='0')
        self.heatmap_cmap_maxval = StringVar(value='1')
        Label(heatmapcolorframe, text='Min: ').grid(row=1, column=0, sticky=(W,E))
        _cm_lower = Entry(heatmapcolorframe, textvariable=self.heatmap_cmap_minval, width=3)
        _cm_lower.grid(row=1, column=1, sticky=(W,E))
        _cm_lower.bind('<Tab>', focus_next_widget)
        _cm_lower.bind('<Return>', self.master.Plotter.update_cmap)
        Label(heatmapcolorframe, text='Max: ').grid(row=1, column=2, sticky=(W,E))
        _cm_upper = Entry(heatmapcolorframe, textvariable=self.heatmap_cmap_maxval, width=3)
        _cm_upper.grid(row=1, column=3, sticky=(W,E))
        _cm_upper.bind('<Tab>', focus_next_widget)
        _cm_upper.bind('<Return>', self.master.Plotter.update_cmap)
        Button(heatmapcolorframe, text='Apply', command=self.master.Plotter.update_cmap).grid(
            row=2, column=1, columnspan=2)
        
  
                   
        HEATMAP_TABS.add(heatmapscaleframe, text='Heatmap Scale')
        HEATMAP_TABS.add(heatmapcolorframe, text='Colors')
        HEATMAP_TABS.pack(expand=1, fill='both')
        
        
        bottom_cmd_frame = Frame(rightpanel)
        bottom_cmd_frame.grid(row=3, column=0, sticky=(N,S,W,E))
        cmd_tab = Notebook(bottom_cmd_frame)
        cmd_frame = Frame(cmd_tab)
        
        self.heka_command = StringVar()
        _cmd_entry = Entry(cmd_frame, width=25, textvariable=self.heka_command)
        _cmd_entry.grid(row=0, column=0, sticky=(E,W))
        _cmd_entry.bind('<Return>', self.send_heka_command)
        Button(cmd_frame, text='Send', command=self.send_heka_command).grid(
            row=0, column=1, sticky=(E,W))
        
        cmd_tab.add(cmd_frame, text='Send HEKA Command')
        cmd_tab.pack(expand=1, fill='both')
        
        
        
        

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
        
        self.amp_params = convert_to_index(self.params['amp'])
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
        
        SECM_TABS.add(approach_curve, text=' Approach Curve ')
        SECM_TABS.add(hopping_mode, text=' Hopping ')
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
        
        Label(piezo_control, text='  X:').grid(row=0, column=0, sticky=(W,E))
        Label(piezo_control, textvariable=self._x_display).grid(row=0, column=1, sticky=(W,E))
        Label(piezo_control, text='  Y:').grid(row=0, column=2, sticky=(W,E))
        Label(piezo_control, textvariable=self._y_display).grid(row=0, column=3, sticky=(W,E))
        Label(piezo_control, text='  Z:').grid(row=0, column=4, sticky=(W,E))
        Label(piezo_control, textvariable=self._z_display).grid(row=0, column=5, sticky=(W,E))
        Label(piezo_control, text= ' (μm)').grid(row=0, column=6, sticky=(W))
        
        Entry(piezo_control, textvariable=self._x_set, width=6).grid(row=1, column=0, columnspan=2, sticky=(W,E))
        Entry(piezo_control, textvariable=self._y_set, width=6).grid(row=1, column=2, columnspan=2, sticky=(W,E))
        Entry(piezo_control, textvariable=self._z_set, width=6).grid(row=1, column=4, columnspan=2, sticky=(W,E))
        Button(piezo_control, text='Set', command=self.piezo_goto).grid(row=1, column=6, sticky=(W,E))
        
        Button(piezo_control, text='Restart Position Monitoring', command=self.piezo_reading_reset).grid(
            row=2, column=0, columnspan=7, sticky=(W,E))
        
        self._z_piezosteps  = StringVar(value='0')
        self._y_piezosteps  = StringVar(value='0')
        
        Label(z_piezo_control, text='Z Steps:').grid(row=0, column=0, sticky=(W,E))
        Entry(z_piezo_control, textvariable=self._z_piezosteps, width=8).grid(row=0, column=1, sticky=(W,E))
        Button(z_piezo_control, text='Go Z', command=self.z_piezo_go).grid(row=0, column=2, sticky=(W,E))
        
        Label(z_piezo_control, text='Y Steps:').grid(row=1, column=0, sticky=(W,E))
        Entry(z_piezo_control, textvariable=self._y_piezosteps, width=8).grid(row=1, column=1, sticky=(W,E))
        Button(z_piezo_control, text='Go Y', command=self.y_piezo_go).grid(row=1, column=2, sticky=(W,E))
        
        Label(z_piezo_control, text='(1000 steps = ~30 μm)').grid(row=0, column=3, sticky=(W))
        Button(z_piezo_control, text='Stop', command=self.z_piezo_stop).grid(row=2, column=1, columnspan=2, sticky=(W,E))
        
        
        PIEZO_TABS.add(piezo_control, text='Piezo')
        PIEZO_TABS.add(z_piezo_control, text='Coarse Piezos')
        PIEZO_TABS.pack(expand=1, fill='both')
        
        
    
        
        
        # Collect all settings for saving/ loading
        self.__settings = {
            'heatmapselection': self.heatmapselection,          # StringVar
            'HeatMapDisplayParam': self.HeatMapDisplayParam,    # Text
            'HeatMapColorMap': self.heatmap_cmap,               # StringVar
            'Heatmap_minval': self.heatmap_cmap_minval,         # StringVar
            'Heatmap_maxval': self.heatmap_cmap_maxval,         # StringVar
            'fig2selection': self.fig2selection,                # StringVar
            'fig2EISselection': self.EIS_view_selection,        # StringVar
            'params': {
                'CV': self.params['CV'],            # dict
                'amp': self.params['amp'],          # dict
                'EIS': self.params['EIS'],          # dict
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
        # Update piezo position fields
        self._x_display.set(f'{self.master.Piezo.x:0.3f}')
        self._y_display.set(f'{self.master.Piezo.y:0.3f}')
        self._z_display.set(f'{self.master.Piezo.z:0.3f}')
        
        # Update time remaining estimate field
        time_est = self.master.FeedbackController.get_time_remaining()
        self._time_est.set(f'{time_est}')
        
        # Update point selection dropdown field
        self.update_fig2_dropdowns()        
        self.root.after(250, self._update_piezo_display)
        
        
    def update_fig2_dropdowns(self):
        '''
        Update Echem figure selection dropdowns based on how many 
        DataPoints are in the experiment and what type is currently selected
        '''
        # Set dropdown to select DataPoint from PointsList
        max_pts = self.master.expt.max_points_per_loc()
        menu_length = self.fig2ptoptmenu['menu'].index("end") + 1
        if (max_pts > 1) and (max_pts != menu_length):
            self.log(f'Detected {max_pts} pts per location, currently {menu_length} in menu', quiet=True)
            menu = self.fig2ptoptmenu['menu']
            menu.delete(0, 'end')
            opts = [i for i in range(max_pts)]
            self.fig2ptoptmenu.set_menu(opts[0], *opts)
            
        # Set dropdown to select display type (I/V/t or EIS-type)
        # if hasattr(self.master.Plotter, 'fig2_datapoint'):
        #     if isinstance(self.master.Plotter.fig2_datapoint, EISDataPoint):
        #         desired_optlist = ['Nyquist', 'Bode Z', 'Bode Phase']
        #         if not all([opt in self.fig2typeoptmenu for opt in desired_optlist]):
                    
        #         pass
        #     else:
        #         menu =
        
    
    def select_next_data(self, *args):
        'Callback from pressing ` (tilde). Plot next echem data in the PointsList'
        menu_length = self.fig2ptoptmenu['menu'].index("end") + 1
        if menu_length == 1:
            return
        current_selection = self.fig2ptselection.get()
        # Find the next index in the list. Loop back to 0 if we're at the end of the list
        next_selection = 0 if current_selection//(menu_length-1) else current_selection + 1
        self.fig2ptselection.set(next_selection)  # Set the new variable
        self.fig_opt_changed(None)                # Send command to update plot
                
            
            
        
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
        self.master.set_expt(expt, name=f.split('/')[-1])
        self.master.Plotter.load_from_expt(expt)
        if hasattr(expt, 'settings') and expt.settings is not None:
            answer = messagebox.askyesno('Load settings', 
                          'Load settings associated with this experiment file?')
            if answer:
                self.load_settings(expt.settings)
    
                
    # Load echem data from csv
    def openEchemFile(self):
        f = filedialog.askopenfilename()
        if not f: return
        point = load_echem_from_file(f)
        if point:
            self.master.Plotter.set_echemdata(DATAPOINT = point)
        else:
            self.log(f'Could not load echem data from file: {f}')
    
    # save current file to disk
    def save(self):
        if self.master.expt:
            settings = self.save_settings(ask_prompt=False)
            self.master.expt.save_settings(settings)
            if self.master.expt.path == 'temp.secmdata':
                return self.saveAs()
            self.master.expt.save()
    
    # save current file under new path
    def saveAs(self):
        if self.master.expt:
            settings = self.save_settings(ask_prompt=False)
            self.master.expt.save_settings(settings)
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
    
    
    def save_settings(self, ask_prompt=True):
        '''
        Convert all user-input fields to a dictionary. Return that settings
        dictionary and (optionally) prompt user to save it to a json file
        '''
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
        if ask_prompt:
            SETTINGS_FILE = filedialog.asksaveasfilename(initialdir='settings/',
                                                     defaultextension='.json')
            if SETTINGS_FILE:
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(settings, f)
                
        return settings
          
    
    
    def load_settings(self, loaded = None):
        '''
        loaded: dictionary of settings
        
        Load user-input field values from a dictionary or from a (prompted) 
        json file
        '''
        if loaded is None:
            if not os.path.exists('./settings/'):
                os.mkdir('./settings')
            SETTINGS_FILE = filedialog.askopenfilename(initialdir='./settings/')
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
            for key in settings_dict:
                if key not in loaded_dict:
                    # Backwards compatibility - may not have had this field
                    # in the past.
                    continue
                field = settings_dict[key]
                value = loaded_dict[key]
                if isinstance(value, dict):
                    settings_dict[key] = set_all(settings_dict[key], value)
                    continue
                set_value(settings_dict[key], value)
            return settings_dict
        
        set_all(self.__settings, loaded)
        
        return
    
    
    def export_heatmap(self):
        if not hasattr(self, 'ExporterGenerator'):
            self.ExporterGenerator = ExporterGenerator()
        exporter = self.ExporterGenerator.get('Heatmap', self, self.master.Plotter.data1.copy())
        
        
    def export_echem_fig(self):
        if not hasattr(self, 'ExporterGenerator'):
            self.ExporterGenerator = ExporterGenerator()
        self.ExporterGenerator.get('Echem', self, self.master.Plotter.ln.get_xydata())
        
        
    def export_heatmap_data(self):
        print('Heatmap data export not implemented')
    
    def export_echem_fig_data(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv')
        if not path:
            return
        # Clear file
        with open(path, 'w') as f:
            f.close()
        pt = self.master.Plotter.fig2DataPoint
        if str(pt) == 'PointsList':
            n_pts = len(pt.data)
            export_both = messagebox.askyesno(title='Export multiple',
                                              message=f'Found {n_pts} echem experiments at this location. Export all of them?')
            if export_both:
                for i in range(n_pts):
                    _pt = pt[i]
                    pt_type = str(_pt)
                    this_path = path.replace('.csv', f'_{pt_type}{i}.csv')
                    if pt_type == 'EISDataPoint':
                        this_path = this_path.replace('.csv', '.txt')
                    _pt._save(this_path)
                    self.log(f'Saved to {this_path}')
                return
            idx = self.fig2ptselection.get()
            pt = pt[idx]
        pt._save(path)        
        self.log(f'Saved to {path}')
        
    def load_SEM_image(self):
        f = filedialog.askopenfilename()
        if not f:
            return
        self.master.ImageCorrelator.load_image(f)
        
     
    ########## DISPLAY FIGURE CALLBACKS ###########
    
    # Selected new view for fig2
    def fig_opt_changed(self, _):
        self.master.Plotter.set_echemdata(
            DATAPOINT = self.master.Plotter.fig2DataPoint,
            forced=True
            )
        return
    
    
    def heatmap_opt_changed(self, *args):
        # selected a new view for heatmap
        option = self.heatmapselection.get()
        value  = self.HeatMapDisplayParam.get()
        
        self.master.Plotter.update_heatmap(option, value)        
        return 'break'
    
    
    def heatmap_rect_zoom(self):
        '''
        Lets user draw a square on the heatmap that will set the bounds
        for the next grid scan. Probably never needed.
        '''
        self.master.Plotter.heatmap_zoom()


    def set_analysis_func(self):
        '''
        Open popup for user to select the analysis function
        '''
        self.master.Plotter.set_analysis_popup()
    
    
    def set_new_area(self):
        '''
        Set the new bounds after heatmap_rect_zoom()
        '''
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
            self.log('Error: PATCHMASTER not opened!')
            return
        new_params = convert_to_index(self.params['amp'])
        cmds = []
        for key, val in new_params.items():
            if key == 'float_gain':
                continue
            cmds.append(f'Set {key} {val}')
        cmds.append('Set E TestDacToStim1 0')
        
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
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run CV while piezo is moving')
            return
        self.set_amplifier()
        E0, E1, E2, E3, v, t0 = self.get_CV_params()
        self.master.HekaWriter.setup_CV(E0, E1, E2, E3, v, t0)
        path = self.master.HekaWriter.run_measurement_loop('CV')
        DataPoint = make_datapoint_from_file(path, 'CVDataPoint')
        if DataPoint:
            self.master.ADC.force_data(DataPoint)
        self.master.make_ready()
        self.log('Finished running CV.')
        return path
    
    
    def get_EIS_params(self):
        eis_params = self.params['EIS'].copy()
        E0      = eis_params['E0'].get('1.0', 'end')
        f0      = eis_params['f0'].get('1.0', 'end')
        f1      = eis_params['f1'].get('1.0', 'end')
        n_pts   = eis_params['n_pts'].get('1.0', 'end')
        n_cycles= eis_params['n_cycles'].get('1.0', 'end')
        amp     = eis_params['amp'].get('1.0', 'end')
        vals = [E0, f0, f1, n_pts, n_cycles, amp]
        try:
            E0, f0, f1, n_pts, n_cycles, amp = [float(val) for val in vals]
            n_pts, n_cycles = int(n_pts), int(n_cycles)
        except:
            print('invalid EIS inputs')
            return 0,0,0,0,0,0
        return E0, f0, f1, n_pts, n_cycles, amp
    
    def run_EIS(self):
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run EIS while piezo is moving')
            return
        eis_params = self.get_EIS_params()
        self.master.HekaWriter.setup_EIS(*eis_params)
        path = self.master.HekaWriter.run_measurement_loop('EIS')
        DataPoint = make_datapoint_from_file(path, 'EISDataPoint', 
                                             applied_freqs=self.master.HekaWriter.EIS_applied_freqs,
                                             corrections=self.master.HekaWriter.EIS_corrections)
        if DataPoint:
            self.master.ADC.force_data(DataPoint)
            DataPoint._save(path[:-4] + '_EIS.asc')
        self.master.make_ready()
        self.log('Finished running EIS')
        return
    
    def run_EIS_corrections(self):
        eis_params = self.get_EIS_params()
        self.master.HekaWriter.setup_EIS(*eis_params, force_waveform_rewrite=True)
        return
        
            
    
    def run_custom(self):
        ''' Run custom, user-set PGF file '''
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run custom waveform while piezo is moving')
            return
        self.set_amplifier()
        E0, E1, E2, E3, v, t0 = self.get_CV_params()
        self.master.HekaWriter.setup_CV(E0, E1, E2, E3, v, t0)
        path = self.master.HekaWriter.run_measurement_loop('Custom')
        DataPoint = make_datapoint_from_file(path, 'CVDataPoint')
        if DataPoint:
            self.master.ADC.force_data(DataPoint)
        self.master.make_ready()
        self.log('Finished running Custom.')
        return path
    
    
    ########## SECM SCAN CALLBACKS ###########
    
    def run_approach_curve(self):
        self.set_amplifier()
        
        height = self.params['approach']['z_height'].get('1.0', 'end')
        height  = float(height)
        
        step_size = self.params['approach']['step_size'].get('1.0', 'end')
        step_size = float(step_size)/1000 # Convert nm -> um

        func = partial(self.master.FeedbackController.approach,
                       height, forced_step_size=step_size)
        run(func)
    
    
    def run_retract(self):
        func = partial(self.master.Piezo.retract, 10, True)
        run(func)
    
        
    def run_automatic_approach(self):
        self.set_amplifier()
        run(self.master.FeedbackController.automatic_approach)
        
    
    def run_hopping(self, img=None):
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run hopping mode while piezo is moving')
            return
        
        fname = filedialog.asksaveasfilename(
                defaultextension='.secmdata', initialdir='D:\SECM\Data')
        if not fname: 
            return
        
        self.set_amplifier()
        func = partial(self._run_hopping, fname, img)
        run(func)
        
    
    def _run_hopping(self, fname, img=None):
        success = self.master.FeedbackController.hopping_mode(self.params['hopping'], img)
        settings = self.save_settings(ask_prompt = False)
        self.master.expt.save_settings(settings)
        self.master.expt.save(fname)
        return success
        
    
    def run_multi_hopping(self):
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run hopping mode while piezo is moving')
            return
        popup = HoppingPopup(self)
        popup.make_popup()
        if not popup.ready:
            return
        
        if not popup.validate_responses():
            return
        
        fname = filedialog.asksaveasfilename(
                defaultextension='.secmdata', initialdir='D:\SECM\Data')
        if not fname: 
            return
        
        n_scans = int(popup.n_scans.get())
        dist    = int(popup.move_dist.get())
        
        func = partial(self._multi_hopping, fname, n_scans, dist)
        run(func)
        
    
    def _multi_hopping(self, fname, n_scans, dist):
        for i in range(n_scans):
            this_fname = fname.replace('.secmdata', f'_{(i+1):03d}.secmdata')
            
            # Run hopping mode scan
            success = self._run_hopping(this_fname)
            
            if not success:
                self.log('Multi hopping aborted due to incomplete scan')
                self.master.Piezo.goto_z(80) # Retract on failed scan
                return
            
            # Move to next spot
            n_steps = self.master.PicoMotor.move_y(-dist)
            if not n_steps:
                self.log('Failed to move y piezo')
                return
            time.sleep(2 + abs(n_steps)/1000)
        
        # Move far away after completing scans
        self.log(f'Multi hopping mode complete. Moving additional {2*dist} um')
        n_steps = self.master.PicoMotor.move_y(-2*dist)
        if not n_steps:
            return
        time.sleep(0.5 + abs(n_steps)/1000)
        return
    
    def run_hopping_image(self): 
        '''
        Run hopping mode scan patterned on user-input binary image
        '''
        img_file = filedialog.askopenfilename(title='Select an image')
        try:
            img = self.master.Piezo.get_xy_coords_from_image(img_file)
        except Exception as e:
            print(f'Error: {e}')
            return
        self.params['hopping']['n_pts'].delete('1.0', 'end')
        self.params['hopping']['n_pts'].insert('1.0', f'{img.shape[0]}')
        self.run_hopping(img)
        return
        
    
    
            
                                                        
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
    
        
    
    def piezo_reading_reset(self):
        self.master.Piezo.start_monitoring()
    
    
    def z_piezo_go(self):
        steps = self._z_piezosteps.get()
        try:
            steps = int(steps)
        except:
            print(f'Invalid input:"{steps}"')
            return
        self.master.PicoMotor.step(steps)
        return
    
    def y_piezo_go(self):
        steps = self._y_piezosteps.get()
        try:
            steps = int(steps)
        except:
            print(f'Invalid input:"{steps}"')
            return
        self.master.PicoMotor.step_y(steps)
        return
    
    
    def z_piezo_stop(self):
        self.master.PicoMotor.halt()
        return
    
    def send_heka_command(self, cmd=None):
        cmd = self.heka_command.get()
        self.master.HekaWriter.send_command(cmd)
        
            


def run_main():
    try:
        master = MasterModule(TEST_MODE = TEST_MODE)
        reader = HekaReader(master)
        writer = HekaWriter(master)
        adc    = ADC(master)
        piezo  = Piezo(master)
        motor  = PicoMotor(master)
        corr   = ImageCorrelator(master)
        fbc    = FeedbackController(master) # must be loaded last
    
    except Exception as e:
        print('Error loading modules: ')
        print(e)
        sel = input('Load in test mode? (y/n) >>>')
        if sel != 'y':
            sys.exit()
        master = MasterModule(TEST_MODE = True)
        reader = HekaReader(master)
        writer = HekaWriter(master)
        adc    = ADC(master)
        piezo  = Piezo(master)
        motor  = PicoMotor(master)
        corr   = ImageCorrelator(master)
        fbc    = FeedbackController(master) # must be loaded last
    
    root = Tk()
    
    try:
        gui = GUI(root, master)
        if master.TEST_MODE:
            print('\nWarning: controller loaded in test mode! Can view data, but cannot control instrument.\n')
        
        gui._update_piezo_display()
        root.after(1000, master.Plotter.update_figs)
        root.bind('<F1>', gui.select_next_data)
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
        root.quit()
        gui.willStop = True

    if not master.TEST_MODE:
        adc.stop()
        piezo.stop()
        motor.stop()
    
    sys.stdout = default_stdout
    sys.stdin  = default_stdin
    sys.stderr = default_stderr


