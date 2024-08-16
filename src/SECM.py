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
# from .modules.HekaIO import HekaReader, HekaWriter
from .modules.Potentiostat import HEKA
from .modules.ADC import ADC
from .modules.Piezo import Piezo
from .modules.FeedbackController import FeedbackController, make_datapoint_from_file, load_echem_from_file
from .modules.Plotter import Plotter, ExporterGenerator
from .modules.DataStorage import Experiment, EISDataPoint, load_from_file
from .modules.Picomotor import PicoMotor
from .modules.ImageCorrelator import ImageCorrelator
from .modules.GUISetup import GUISetupMethods, convert_to_index
from .utils.utils import run, Logger, threads
from .gui.hopping_popup import HoppingPopup
default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr

matplotlib.use('TkAgg')

TEST_MODE = False



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
        
        
    def register(self, module, alias=None):
        # register a submodule to master
        if not alias:
            alias = module.__class__.__name__
        setattr(self, alias, module)
        self.modules.append(getattr(self, alias))
        self.log(f'Loaded {module.__class__.__name__} as master.{alias}')
    
    
    def set_expt(self, expt, name=None):
        self.check_save()
        self.expt = expt
        title = name if name else 'SECM Controller'
        self.GUI.root.title(title)
            
    
    
    def check_save(self):
        if not self.expt.isSaved():
            self.GUI.savePrevious()
    
    
    @threads.new_thread
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
        self.Potentiostat._abort()
        if not self.STOP:
            # Reset
            self.make_ready()
    
    
    @threads.new_thread
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
        self.textbox.tag_config('blue', foreground='blue')
        self.textbox.tag_config('green', foreground='green')

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
    



class GUI(Logger, GUISetupMethods):
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
        
        
        ### SET UP FRAMES ###
        
        leftpanel  = Frame(self.root)
        rightpanel = Frame(self.root)
        ConsoleFrame = Frame(self.root)
        leftpanel.grid(row=0, column=0, sticky=(N,S,E,W))
        rightpanel.grid(row=0, column=1, sticky=(N,S,E,W))
        ConsoleFrame.grid(row=1, column=0, columnspan=2, sticky=(N,S,E,W))
        console = Text(ConsoleFrame, width=125, height=10)
        console.grid(row=0, column=0, sticky=(N,S,E,W))
        
 
        StopButtonFrame = Frame(leftpanel)
        PstatFrame      = Frame(leftpanel)
        SECMFrame       = Frame(leftpanel)
        PiezoFrame      = Frame(leftpanel)
        StopButtonFrame.grid(row=0, column=0, sticky=(N,S,E,W))
        PstatFrame.grid(row=1, column=0, sticky=(N,S,E,W))
        SECMFrame.grid(row=2, column=0, sticky=(N,S,E,W))
        PiezoFrame.grid(row=3, column=0, sticky=(N,S,E,W))
        
        HeatmapFrame = Frame(rightpanel)
        EchemFrame   = Frame(rightpanel)
        OptionFrame  = Frame(rightpanel)
        HeatmapFrame.grid(row=0, column=0, sticky=(N,S,E,W))
        Separator(rightpanel, orient='vertical').grid(row=0, column=1, 
                                                      padx=5,sticky=(N,S))
        EchemFrame.grid(row=0, column=2, sticky=(N,S,E,W))
        Separator(rightpanel, orient='horizontal').grid(row=1, column=0, 
                                                        columnspan=10, pady=5,
                                                        sticky=(W,E))
        OptionFrame.grid(row=2, column=0, columnspan=10, sticky=(N,S,E,W))
        
        
        
        # All inherited from GUISetupMethods
        self.MakeHeatmapFrame(HeatmapFrame)
        self.MakeEchemFrame(EchemFrame)
        
        # Initialize plotter
        Plotter(self.master, self.HeatmapFig, self.EchemFig)
        
        self.MakeStopButtonFrame(StopButtonFrame)
        self.MakePstatFrame(PstatFrame)
        self.MakeSECMFrame(SECMFrame)
        self.MakePiezoFrame(PiezoFrame)
        self.MakeOptionFrame(OptionFrame)
                
        
        
        # Send print messages to the console
        sys.stdout = PrintLogger(console)
        
        # Collect all settings for saving/ loading
        self.__settings = {
            'heatmapselection': self.heatmapselection,          # StringVar
            'HeatMapDisplayParam': self.HeatMapDisplayParam,    # StringVar
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
        self.master.run()
        if hasattr(self.master, 'HekaReader'):
            self.master.HekaReader.read()
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
            self.master.Plotter.EchemFig.set_datapoint(point, forced=True)
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
        exporter = self.ExporterGenerator.get('Heatmap', self, self.master.Plotter.Heatmap.data.copy())
        
        
    def export_echem_fig(self):
        if not hasattr(self, 'ExporterGenerator'):
            self.ExporterGenerator = ExporterGenerator()
        self.ExporterGenerator.get('Echem', self, self.master.Plotter.EchemFig.ln.get_xydata())
        
        
    def export_heatmap_data(self):
        print('Heatmap data export not implemented')
    
    def export_echem_fig_data(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv')
        if not path:
            return
        # Clear file
        with open(path, 'w') as f:
            f.close()
        pt = self.master.Plotter.EchemFig.DataPoint
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
        self.master.Plotter.EchemFig.set_datapoint(
            DataPoint = self.master.Plotter.EchemFig.DataPoint,
            forced=True
            )
        return
    
    
    def reset_ADC_monitor(self):
        self.master.Plotter.EchemFig.reset()
    
    
    def heatmap_opt_changed(self, *args):
        # selected a new view for heatmap
        # option = self.heatmapselection.get()
        # value  = self.HeatMapDisplayParam.get()
        
        self.master.Plotter.update_heatmap()        
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
        # corners = self.master.Plotter.RectangleSelector.get_coords()
        # if all([c == (0,0) for c in corners]):
        #     return
        # scale = self.master.Piezo.set_new_scan_bounds(corners)
        # gui.params['hopping']['size'].delete('1.0', 'end')
        # gui.params['hopping']['size'].insert('1.0', f"{scale:0.3f}")
        return
    
    
    ########## ELECTROCHEMISTRY CALLBACKS ###########
    
    # Set the potentiostat amplifier (filters, gain, etc)  
    def set_amplifier(self):
        self.master.Potentiostat.set_amplifier()
    
    
    def get_amplifier_params(self):
        params = convert_to_index(self.params['amp'])
        return params
    
    
    def get_CV_params(self):
        cv_params = self.params['CV'].copy()
        strs = ['E0', 'E1', 'E2', 'Ef', 'v', 't0']
        try:
            E0, E1, E2, E3, v, t0 = map(float,
                                        [cv_params[x].get() for x in strs])

        except Exception as e:
            print('Error: invalid CV inputs')
            print(e)
            return 0,0,0,0,0,0
        return E0, E1, E2, E3, v, t0
    
    
    
    def run_CV(self, _new_thread=True):
        if _new_thread:
            # Run a CV and process the data in a new thread.
            return self._run_CV_thread()
        else:
            # Run a CV and process the data in the thread that called this function.
            # Used when approach curve finds the surface (runs in automatic_approach thread)
            return self._run_CV_noThread()
    
    
    @threads.new_thread
    def _run_CV_thread(self):
        return self._run_CV()
    
    
    def _run_CV_noThread(self):
        return self._run_CV()
       
    
    def _run_CV(self):
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run CV while piezo is moving')
            return
        self.master.Potentiostat.set_amplifier()
        self.master.Potentiostat.setup_CV()
        path = self.master.Potentiostat.run_CV()
        if not path: return
        
        DataPoint = make_datapoint_from_file(path, 'CVDataPoint')
        if DataPoint:
            self.master.ADC.force_data(DataPoint)
        
        self.master.make_ready()
        self.log('Finished running CV.')
        return path
    
    
    def get_EIS_params(self):
        eis_params = self.params['EIS'].copy()
        strs = ['E0', 'f0', 'f1', 'n_pts', 'n_cycles', 'amp']
        try:
            vals = map(float, [eis_params[x].get() for x in strs])
            E0, f0, f1, n_pts, n_cycles, amp = vals
            n_pts, n_cycles = int(n_pts), int(n_cycles)
        except:
            print('Error: invalid EIS inputs')
            return 0,0,0,0,0,0
        return E0, f0, f1, n_pts, n_cycles, amp
    
    
    @threads.new_thread
    def run_EIS(self):
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run EIS while piezo is moving')
            return
        self.reset_ADC_monitor()
        self.master.Potentiostat.setup_EIS()
        path = self.master.Potentiostat.run_EIS()
        if not path: return
        
        DataPoint = make_datapoint_from_file(path, 'EISDataPoint', 
                                             applied_freqs=self.master.Potentiostat.EIS_freqs,
                                             corrections=self.master.Potentiostat.EIS_corrections)
        if DataPoint:
            self.master.ADC.force_data(DataPoint)
            DataPoint._save(path[:-4] + '_EIS.asc')
        self.master.make_ready()
        self.log('Finished running EIS')
        return
    
    
    @threads.new_thread
    def run_EIS_corrections(self):
        self.master.Potentiostat.setup_EIS(force_waveform_rewrite=True)
        return
    
    def get_CA_params(self):
        ca_params = self.params['CA'].copy()
        strs = ['voltage', 't']
        try:
            voltage, t = map(float,
                                        [ca_params[x].get() for x in strs])

        except Exception as e:
            print('Error: invalid CV inputs')
            print(e)
            return 0,0
        return voltage, t
    

    @threads.new_thread
    def run_CA(self):
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run CV while piezo is moving')
            return
        self.master.Potentiostat.set_amplifier()
        self.master.Potentiostat.setup_CA()
        path = self.master.Potentiostat.run_CA()
        if not path: return
        
        DataPoint = make_datapoint_from_file(path, 'CVDataPoint')
        if DataPoint:
            self.master.ADC.force_data(DataPoint)
        
        self.master.make_ready()
        self.log('Finished running CA.')
        return path
        
            
    @threads.new_thread
    def run_custom(self):
        ''' Run custom, user-set PGF file '''
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run custom waveform while piezo is moving')
            return
        self.reset_ADC_monitor()
        self.master.Potentiostat.set_amplifier()
        path = self.master.Potentiostat.run_custom()
        if not path: return 
        
        DataPoint = make_datapoint_from_file(path, 'CVDataPoint')
        if DataPoint:
            self.master.ADC.force_data(DataPoint)
        self.master.make_ready()
        self.log('Finished running Custom.')
        return path
    
    
    ########## SECM SCAN CALLBACKS ###########
    
    @threads.new_thread
    def run_approach_curve(self):
        self.reset_ADC_monitor()
        self.set_amplifier()
        
        height = self.params['approach']['z_height'].get()
        height  = float(height)
        
        step_size = self.params['approach']['step_size'].get()
        step_size = float(step_size)/1000 # Convert nm -> um

        self.master.FeedbackController.approach(height, forced_step_size=step_size)
    
    
    @threads.new_thread
    def run_retract(self):
        self.master.Piezo.retract(10, True)
    
    
    @threads.new_thread    
    def run_automatic_approach(self):
        self.set_amplifier()
        self.reset_ADC_monitor()
        self.master.FeedbackController.automatic_approach()
        
    
    def run_hopping(self, img=None):
        if self.master.Piezo.isMoving():
            self.log('Error: cannot run hopping mode while piezo is moving')
            return
        
        fname = filedialog.asksaveasfilename(
                defaultextension='.secmdata', initialdir='D:\SECM\Data')
        if not fname: 
            return
        
        self.set_amplifier()
        self._run_hopping(fname, img)
        
    
    @threads.new_thread
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
        
        self._multi_hopping(fname, n_scans, dist)
        
    
    @threads.new_thread
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
        self.params['hopping']['n_pts'].set(f'{img.shape[0]}')
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
    
        
            


def run_main():
    try:
        master = MasterModule(TEST_MODE = TEST_MODE)
        pstat = HEKA(master)
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
            master.endState()
            sys.exit()
        master.endState() # Close already-opened modules
        
        master = MasterModule(TEST_MODE = True)
        pstat  = HEKA(master)
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


