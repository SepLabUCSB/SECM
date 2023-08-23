import numpy as np
import time
from io import StringIO
import os
import scipy.io
import datetime
from functools import partial
from ..utils.utils import run, Logger
from .DataStorage import (Experiment, CVDataPoint, EISDataPoint,
                                 PointsList)
from ..analysis.analysis_funcs import E0_finder_analysis




def read_heka_data(file):
    '''
    Parse PATCHMASTER-output csv files.
    
    Use StringIO to parse through file (fastest method I've found)
    Convert only floats to np arrays
    '''
    if file == 'MEAS_ABORT':
        return 0,0,0
    
    if file.endswith('.mat'):
        return extract_matlab_iv_data(file)
    
    def isFloat(x):
        try: 
            float(x)
            return True
        except: 
            return False
    
    s = StringIO()
    with open(file, 'r') as f:
        for line in f:
            if isFloat(line.split(',')[0]):
                # Check for index number
                s.write(line)
    if s.getvalue() != '':
        s.seek(0)
        array = np.genfromtxt(s, delimiter=',')
        array = array.T
        _, t, i, _, v = array
        return t, v, i
    

def extract_matlab_iv_data(file):
    '''
    Extracts I-V type data from a PATHCMASTER-generated .mat file.
    Assumes Trace 1 in PATCHMASTER is I (Current)
    Assumes Trace 2 in PATCHMASTER is V (Voltage)
    
    Returns times, voltages, currents
    
    Exporting binary .mat files from PATCHMASTER is much, much faster
    than exporting as csv files    
    '''
    d = scipy.io.loadmat(file)
    
    
    sweeps = []
    traces = []
    for key in d.keys():
        if not key.startswith('Trace'):
            continue
        a,b,c, sweep, trace = key.split('_')
        sweeps.append(int(sweep))
        traces.append(int(trace))
        
    sweeps = list(set(sweeps))
    traces = list(set(traces))
    
    T = np.array([])
    V = np.array([])
    I = np.array([])
    
    for sweep in sweeps:
        for trace in traces:
            key = f'{a}_{b}_{c}_{sweep}_{trace}'
            arr = d[key]                         # [ [t1, v1], [t2, v2], ...]
            arr = arr.transpose()                # [ [t1, t2, ...], [v1, v2, ...] ]
            ts, vals = arr
            if trace == traces[0]:
                T = np.append(T,ts)
            if trace == 1:
                I = np.append(I, vals)
            elif trace == 2:
                V = np.append(V, vals)
                
    return T, V, I


def make_datapoint_from_file(file:str, DataPointType:str):
    '''
    Used for plotting echem which was recorded outside of a heatmap.
    
    Reads HEKA data from given file path. Returns a DataPoint of the
    type specified by DataPointType.
    
    file: string, path to data file
    DataPointType: string, one of 'CVDataPoint', 'EISDataPoint'
    '''
    t, v, i = read_heka_data(file)
    if DataPointType == 'CVDataPoint':
        return CVDataPoint(loc=(0,0,0), data = [t,v,i])
    if DataPointType == 'EISDataPoint':
        return EISDataPoint(loc=(0,0,0), data = [t,v,i], applied_freqs=None)
    else:
        print('Invalid DataPointType')
        return
    
    




class FeedbackController(Logger):
    '''
    Class to glue HEKA communication, Piezo, ADC, data storage,
    and data plotting together.
    

    '''
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        # Get local refs to other modules
        self.Piezo = self.master.Piezo
        self.ADC = self.master.ADC
        self.HekaWriter = self.master.HekaWriter
        
        self.est_time_remaining = 0
        
        self._is_running = False
        self._piezo_counter = self.Piezo.counter
    
        
    def get_time_remaining(self):
        '''
        Returns string with the estimated time remaining in the experiment
        in format "00 hr 00 min 00 s"
        '''
        s = self.est_time_remaining
        hr  = int(np.floor(s/3600))
        mi  = int(np.floor((s - hr*3600)/60))
        sec = int(s - hr*3600 - mi*60)
        return f'{hr:02} hr, {mi:02} min, {sec:02} s'
    
    
    def automatic_approach(self):
        '''
        Procedure which runs approach curve using XYZ piezo. If the surface
        is not reached, step the PicoMotor up ~60 nm. Continue running approach
        curves until the surface is found.
        '''
        height = 80
        if self._is_running:
            self.log('Received another command but already running!')
            return
        
        # Wait for potential to equilibrate
        voltage = self.master.GUI.params['approach']['voltage'].get('1.0', 'end')
        voltage = float(voltage) 
        self.Piezo.goto(80,80,height)
        self.HekaWriter.macro('E Vhold 0')
        time.sleep(1)
        self.HekaWriter.macro('E AutoCFast')
        self.HekaWriter.macro(f'E Vhold {voltage}')
        
        while True:
            if self.master.ABORT:
                break
            
            time.sleep(3)
            _, on_surface = self.approach(height=height)
            
            if self.master.ABORT:
                break
            
            if on_surface:
                # Take a CV on the surface
                self.master.GUI.run_CV()
                # Slowly retract from surface by 10 um
                self.Piezo.retract(10, relative=True)
                break
            
            self.Piezo.goto(80,80,height)
            time.sleep(0.05)
            self.master.PicoMotor.step(2000) # 2000 steps ~= 60 um
            time.sleep(3)    
        # time.sleep(1)
        self.Piezo.start_monitoring()
        return
    
    
    def approach(self, height:float=None, voltage:float=400, 
                 start_coords:tuple=None, forced_step_size=None):
        '''
        Run an approach curve. If no parameters are given, start from 
        the current position. Otherwise, start from the set height, or
        from the set coordinates.
        
        voltage: float, mV
        start_coords: tuple, (x,y,z). Starting point to approach from
        
        Step probe closer to surface starting at point (x,y,z). 
        Stop when measured i > i_cutoff
        '''
        
        # Get cutoff current from GUI
        voltage = self.master.GUI.params['approach']['voltage'].get('1.0', 'end')
        cutoff  = self.master.GUI.params['approach']['cutoff'].get('1.0', 'end')
        speed   = self.master.GUI.params['approach']['approach_speed'].get('1.0', 'end')
        rel_opt = self.master.GUI.params['approach']['rel_current'].get()
        try:
            voltage = float(voltage)
            i_cutoff = float(cutoff) * 1e-12
            speed = float(speed)
            use_rel_I = True if rel_opt == 'Relative' else False
        except Exception as e:
            print('Invalid approach curve entry!')
            print(e)
            return
        
        
        # Setup piezo
        if not start_coords:
            start_coords = self.Piezo.measure_loc()
        x, y, z_start = start_coords
        if height:
            z_start = height
            
        self.log(f'Starting approach curve from {x}, {y}, {z_start}')
        self.Piezo.stop_monitoring()
        # self.Piezo.goto(x, y, z_start)
        
        
        # Setup potentiostat and ADC
        self.HekaWriter.macro(f'E Vhold {voltage}')
        gain  = 1e9 * self.master.GUI.amp_params['float_gain']
        srate = 1000
        self.ADC.set_sample_rate(srate)
        run(partial(self.ADC.polling, 5000))
        time.sleep(0.005)
        
        
        # Measure background current if needed
        baseline_I = 0
        if use_rel_I:
            time.sleep(1)
            _,_,I = self.ADC.pollingdata.get_data(int(0.8*srate))
            baseline_I = np.mean(I)
            self.log(f'Measured background current of {baseline_I/gain:0.2e}')
        
        

        # Start it
        self._piezo_counter = self.Piezo.counter # Counter tracks when piezo stops
        run(partial(self.Piezo.approach, speed, forced_step_size))
        
        on_surface = False
        time.sleep(0.1)
        self.master.Plotter.FIG2_FORCED = True # Don't draw ADC data
        while True:
            '''
            Loop checks if approach curve is finished due to
            1. global abort
            2. piezo at movement limit
            3. current > cutoff criterium
            '''
            if self.master.ABORT:
                self.log('Stopped approach on abort')
                break
            if self.Piezo.counter != self._piezo_counter:
                self.log('Piezo stop detected')
                break
            
            _, _, I = self.ADC.pollingdata.get_data(10)
            I = np.abs(np.array(I) - baseline_I)
            I /= gain # convert V -> I
            if any([val > i_cutoff for val in I]):
                self.Piezo.halt()
                on_surface = True
                break
            time.sleep(0.001)
        
        if on_surface:
            self.log('Found surface')
        else:
            self.log('Did not find surface')
        
        self.ADC.STOP_POLLING()  
        self.Piezo.start_monitoring()
        self.master.Plotter.FIG2_FORCED = False
        self._piezo_counter = self.Piezo.counter
        return self.Piezo.z, on_surface
    
    
    def hopping_mode(self, params):
        '''
        Run a hopping mode scan.
        
        Runs in its own thread!
        
        '''
        # TODO: extend this to handle constant voltage hopping mode
        length = params['size'].get('1.0', 'end')
        height = params['Z'].get('1.0', 'end')
        n_pts  = params['n_pts'].get('1.0', 'end')
        expt_type = params['method'].get()
        
        length = float(length) 
        z_max  = float(height)
        n_pts  = int(n_pts)
        
        
        # Setup potentiostat for experiment
        if not self.potentiostat_setup(expt_type):
            self.log('Failed to set up potentiostat! Cannot run hopping mode')
            return False
                                
        # Starts scan from Piezo.starting_coords
        points, order = self.Piezo.get_xy_coords(length, n_pts) 
        
        # Initialize data storage 
        expt = Experiment(points    = points,
                          order     = order,
                          expt_type = expt_type)
            
        
        self.master.set_expt(expt)
        self.master.Plotter.set_axlim('fig1',
                                      xlim=(0,length),
                                      ylim=(0,length)
                                      )
        x,y,z = self.Piezo.measure_loc()
        self.log(f'Starting hopping mode {expt_type} scan')
        self.log(f'Starting approach curves from {height.strip()}')
        
        # height < 0 means retract that amount at each point
        if z_max < 0:
            retract_distance = -z_max
            forced_step_size = 0.005
        else:
            retract_distance = 6
            forced_step_size = None
        
        point_times = []
        
        for i, (x, y) in enumerate(points[:-2]):
            pt_st_time = time.time()
            # Retract from surface
            if (i !=0) and (not self.master.TEST_MODE):
                # z = self.Piezo.retract(height=retract_distance, 
                #                         relative=True)
                tx, ty, tz = self.Piezo.measure_loc()
                self.Piezo.goto_z(tz+retract_distance)
                time.sleep(0.5)
                _,_,z = self.Piezo.measure_loc()
                time.sleep(0.5)
            
            # Retract to the given z_max, otherwise start from next (x,y) but current z
            if z_max > 0:
                z = z_max
            self.Piezo.goto(x, y, z)
            
            time.sleep(0.1)
            if self.master.ABORT:
                self.log('Hopping mode aborted')
                return False
            
            # Run approach at this point
            z, on_surf = self.approach(forced_step_size=forced_step_size)
            if not on_surf:
                self.log('Hopping mode ended due to not reaching surface')
                return False
                        
            # Run echem experiment on surface
            data = self.run_echems(expt_type, expt, (x, y, z), i) # TODO: run variable echem experiment(s) at each pt
            if not data:
                # Aborted during HEKA measurement
                self.log('Hopping mode aborted')
                return False
            
            # Save data
            grid_i, grid_j = order[i]  
            expt.set_datapoint( (grid_i, grid_j), data)
            
            # Send data for plotting
            self.master.Plotter.update_heatmap()
            
            expt.save()
            time.sleep(0.01)
            
            # Recalculate remaining time
            point_times.append(time.time() - pt_st_time)
            avg_time = np.mean(point_times)
            self.est_time_remaining = (len(points[:-2]) - (i+1))*avg_time
        
        # z = self.Piezo.retract(height=80, relative=False)
        self.Piezo.goto_z(80)
        time.sleep(0.1)
        self.Piezo.goto(80,80,80)
        self.est_time_remaining = 0
        
        return True

    ###############################
    #### POTENTIOSTAT CONTROLS ####
    ###############################
    
    def potentiostat_setup(self, expt_type):
        if self.master.TEST_MODE:
            return True
        
        if expt_type in ('CV', 'Custom'):
            self.master.GUI.set_amplifier()
            CV_vals = self.master.GUI.get_CV_params()
            if CV_vals == (0,0,0,0,0,0):
                return False
            self.master.HekaWriter.setup_CV(*CV_vals)
            return True
        
        if expt_type == 'EIS':
            self.master.GUI.set_amplifier()
            EIS_vals = self.master.GUI.get_EIS_params()
            if EIS_vals == (0,0,0,0,0):
                return False
            self.master.HekaWriter.setup_EIS(*EIS_vals)
            return True
        
        if expt_type == 'CV then EIS':
            # We setup potentiostat settings twice at each point:
            # first for CV then for EIS. Done in run_echems()
            return True
        
        # if expt_type == 'Custom':
        #     self.master.GUI.set_amplifier()
        #     return True
        
        return False
    
    
    def run_echems(self, expt_type, expt, loc, i):
        '''
        Run echem experiments defined by expt_type at loc (x,y,z).
        
        Save .asc(s) to appropriate folder
        
        Return         
        '''
        if expt_type == 'CV':
            t, voltage, current = self.run_CV(expt.path, i)
            if type(t) == int:
                return None
            data = CVDataPoint(loc = loc, data = [t, voltage, current])
        
        if expt_type == 'EIS':
            t, voltage, current = self.run_EIS(expt.path, i)
            if type(t) == int:
                return None
            data = EISDataPoint(loc = loc, data = [t, voltage, current],
                                applied_freqs = self.HekaWriter.EIS_applied_freqs)
         
        if expt_type == 'Custom':
            t, voltage, current = self.run_custom(expt.path, i)
            if type(t) == int:
                return None
            data = CVDataPoint(loc = loc, data = [t, voltage, current])   
         
        if expt_type == 'CV then EIS':
            # Run CV
            if not self.potentiostat_setup('CV'): 
                return None
            t, voltage, current = self.run_CV(expt.path, i)
            if type(t) == int:
                return None
            CVdata = CVDataPoint(loc=loc, data=[t,voltage,current])
            
            # Check for peak detection
            CVdata = E0_finder_analysis(CVdata, '')
            start_V = voltage[0]
            E0 = CVdata.analysis[(E0_finder_analysis, '')]
            if E0 == 0:
                return CVdata
            
            # Run EIS: Set DC bias
            self.log(f'Detected E0 = {E0:0.3f} V')
            self.master.GUI.params['EIS']['E0'].delete('1.0', 'end')
            self.master.GUI.params['EIS']['E0'].insert('1.0', f'{E0*1000:0.1f}')
            if not self.potentiostat_setup('EIS'): 
                return None
            time.sleep(2)
            
            
            # Run EIS expt
            t, voltage, current = self.run_EIS(expt.path, i)
            if type(t) == int:
                return None
            self.HekaWriter.reset_amplifier()
            self.HekaWriter.send_command(f'Set E Vhold {start_V}')
            time.sleep(2)
            EISdata = EISDataPoint(loc = loc, data = [t, voltage, current],
                                   applied_freqs = self.HekaWriter.EIS_applied_freqs)
            data = PointsList(loc=loc, data = [CVdata, EISdata])
    
        return data
    
    
    def fake_CV(self, i):
        # Generate fake data for testing piezo
        t = np.linspace(0,1,50)
        voltage = np.linspace(0, 0.5, 50)
        max_I = 100*np.random.rand()
        current = np.linspace(0, i*1e-9, 50)
        return t, voltage, current
    
    
    def run_CV(self, save_path, name):
        '''
        Send command to run CV with the current parameters and save the data
        '''
        if self.master.TEST_MODE:
            return self.fake_CV(name)
        
        if save_path.endswith('.secmdata'):
            save_path = save_path.replace('.secmdata', '')
            
        path = self.master.HekaWriter.run_measurement_loop(
                                           'CV',
                                           save_path=save_path,
                                           name=name
                                           )
        t, v, i = read_heka_data(path)
        return t, v, i
    
    
    def run_EIS(self, save_path, name):
        if self.master.TEST_MODE:
            t = np.arange(0,1,1000)
            return [t, np.sin(t), np.cos(t)]
        
        if save_path.endswith('.secmdata'):
            save_path = save_path.replace('.secmdata', '')
            
        path = self.master.HekaWriter.run_measurement_loop(
            'EIS', save_path = save_path, name=name)
        
        t, v, i = read_heka_data(path)
        return t, v, i
    
    
    def run_custom(self, save_path, name):
        if self.master.TEST_MODE:
            return self.fake_CV(name)
        
        if save_path.endswith('.secmdata'):
            save_path = save_path.replace('.secmdata', '')
            
        path = self.master.HekaWriter.run_measurement_loop(
            'Custom', save_path = save_path, name=name)
        
        t, v, i = read_heka_data(path)
        return t, v, i
    

    
    
    
    
    


