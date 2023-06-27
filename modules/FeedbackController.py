import numpy as np
import time
from io import StringIO
import os
from functools import partial
from utils.utils import run, Logger
from modules.DataStorage import Experiment, CVDataPoint




def read_heka_data(file):
    # Use StringIO to parse through file (fastest method I've found)
    # Convert only floats to np arrays
    
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
        return array
    




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
        
        self._is_running = False
        self._piezo_counter = self.Piezo.counter
    
    
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
        self.Piezo.goto(0,0,height)
        self.HekaWriter.macro(f'E Vhold {voltage}')
        
        while True:
            if self.master.ABORT:
                break
            
            time.sleep(3)
            _, on_surface = self.approach(height=height)
            
            if self.master.ABORT:
                break
            
            if on_surface:
                # Slowly retract from surface by 10 um
                self.Piezo.retract(10, relative=True)
                break
            
            self.Piezo.goto(0,0,height)
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
        try:
            voltage = float(voltage)
            i_cutoff = float(cutoff) * 1e-12
            speed = float(speed)
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
        gain = 1e9 * self.master.GUI.amp_params['float_gain']
        self.ADC.set_sample_rate(200)
        run(partial(self.ADC.polling, 5000))
        time.sleep(0.005)
        

        # Start it
        self._piezo_counter = self.Piezo.counter # Counter tracks when piezo stops
        run(partial(self.Piezo.approach, speed, forced_step_size))
        
        on_surface = False
        time.sleep(0.1)
        while True:
            '''
            Loop checks if approach curve is finished due to
            1. global abort
            2. piezo at movement limit
            3. current > cutoff criterium
            '''
            if self.master.ABORT:
                self.log('stopped approach on abort')
                break
            if self.Piezo.counter != self._piezo_counter:
                self.log('piezo stopped')
                break
            
            _, _, I = self.ADC.pollingdata.get_data(10)
            I = np.abs(np.array(I))
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
            return
                                
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
        self.log(f'Starting approach curves from {height}')
        
        # height == -1 means retract the minimum amount at each point
        if z_max == -1:
            forced_step_size = 0.01
        else:
            forced_step_size = None
        
        for i, (x, y) in enumerate(points[:-2]):
            
            # Retract from surface
            if (i !=0) and (not self.master.TEST_MODE):
                z = self.Piezo.retract(height=6, relative=True)
            
            # Retract to the given z_max, otherwise start from next (x,y) but current z
            if z_max != -1:
                z = z_max
            self.Piezo.goto(x, y, z)
            
            time.sleep(0.1)
            if self.master.ABORT:
                self.log('Hopping mode aborted')
                return
            
            # Run approach at this point
            z, on_surf = self.approach(forced_step_size=forced_step_size)
            if not on_surf:
                self.log('Hopping mode ended due to not reaching surface')
                return
                        
            # Run echem experiment on surface
            data = self.run_echems(expt_type, expt, (x, y, z), i) # TODO: run variable echem experiment(s) at each pt
            
            # Save data
            grid_i, grid_j = order[i]  
            expt.set_datapoint( (grid_i, grid_j), data)
            
            # Send data for plotting
            self.master.Plotter.update_heatmap()
            
            expt.save()
            time.sleep(0.01)
        
        
        
        # self.Piezo.goto(curr_x, curr_y, z_max)
        # self.master.expt = expt
            
        return 

    ###############################
    #### POTENTIOSTAT CONTROLS ####
    ###############################
    
    def potentiostat_setup(self, expt_type):
        if self.master.TEST_MODE:
            return True
        
        if expt_type == 'CV':
            self.master.GUI.set_amplifier()
            CV_vals = self.master.GUI.get_CV_params()
            if CV_vals == (0,0,0,0,0,0):
                return False
            self.master.HekaWriter.setup_CV(*CV_vals)
            return True
        
        if expt_type == 'Custom':
            self.master.GUI.set_amplifier()
            return True
        
        return False
    
    
    def run_echems(self, expt_type, expt, loc, i):
        '''
        Run echem experiments defined by expt_type at loc (x,y,z).
        
        Save .asc(s) to appropriate folder
        
        Return         
        '''
        if expt_type == 'CV':
            voltage, current = self.run_CV(expt.path, i)
                
            data = CVDataPoint(loc = loc, data = [np.linspace(0,1,len(voltage)),
                                                   voltage, current])
        
        if expt_type == 'Custom':
            voltage, current = self.run_custom(expt.path, i)
            
            data = CVDataPoint(loc = loc, data = [np.linspace(0,1,len(voltage)),
                                                   voltage, current])
                        
        return data
    
    def fake_CV(self, i):
        # Generate fake data for testing piezo
        voltage = np.linspace(0, 0.5, 50)
        max_I = 100*np.random.rand()
        current = np.linspace(0, i*1e-9, 50)
        return voltage, current
    
    
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
        output = read_heka_data(path)
        _, t, i, _, v = output
        return v, i
    
    
    def run_custom(self, save_path, name):
        if self.master.TEST_MODE:
            return self.fake_CV(name)
        
        if save_path.endswith('.secmdata'):
            save_path = save_path.replace('.secmdata', '')
            
        path = self.master.HekaWriter.run_measurement_loop(
            'Custom', save_path = save_path, name=name)
        
        output = read_heka_data(path)
        _, t, i, _, v = output
        return v, i
    

    
    
    
    
    


