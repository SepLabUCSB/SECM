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
        
        while True:
            if self.master.ABORT:
                break
            
            time.sleep(3)
            _, on_surface = self.approach(height=height)
            
            if self.master.ABORT:
                break
            
            if on_surface:
                # Slowly retract from surface by 10 um
                self.Piezo.retract(10, 1, relative=True)
                break
            
            self.Piezo.goto(0,0,height)
            time.sleep(0.05)
            self.master.PicoMotor.step(2000) # 2000 steps ~= 60 um
            time.sleep(3)    
        # time.sleep(1)
        # self.Piezo.start_monitoring()
        return
    
    
    def approach(self, height:float=None, voltage:float=400, 
                 start_coords:tuple=None):
        '''
        voltage: float, mV
        start_coords: tuple, (x,y,z). Starting point to approach from
        
        Step probe closer to surface starting at point (x,y,z). 
        Stop when measured i > i_cutoff
        '''
        
        # Get cutoff current from GUI
        cutoff = self.master.GUI.params['approach']['cutoff'].get('1.0', 'end')
        speed  = self.master.GUI.params['approach']['approach_speed'].get('1.0', 'end')
        try:
            i_cutoff = float(cutoff) * 1e-12
        except:
            print('Invalid approach cutoff: {cutoff}')
            return
        
        try:
            speed = float(speed)
        except:
            print('Invalid approach speed: {speed}')
            return
        
        # Setup piezo
        if not start_coords:
            start_coords = (0,0,80)
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
        run(partial(self.ADC.polling, 3000))
        time.sleep(0.005)
        

        # Start it
        self._piezo_counter = self.Piezo.counter # Counter tracks when piezo stops
        run(partial(self.Piezo.approach, speed))
        
        on_surface = False
        time.sleep(0.1)
        while True:
            if self.master.ABORT:
                self.log('stopped approach on abort')
                break
            # if not self.Piezo._moving:
            #     self.log('Piezo stopped moving')
            #     break
            if self.Piezo.counter != self._piezo_counter:
                self.log('piezo stopped')
                break
            
            _, _, I = self.ADC.pollingdata.get_data()
            I = np.abs(np.array(I[-10:]))
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
    
    
    def fake_CV(self, i):
        # Generate fake data for testing piezo
        voltage = np.linspace(0, 0.5, 50)
        max_I = 100*np.random.rand()
        current = np.linspace(0, i*1e-9, 50)
        return voltage, current
    
    
    def run_CV(self, save_path, name):
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
                        
        return data
    
    
    def hopping_mode(self, params, expt_type='CV'):
        '''
        Run a hopping mode scan.
        
        Runs in its own thread!
        
        '''
        # TODO: extend this to handle constant voltage hopping mode
        length = params['size'].get('1.0', 'end')
        height = params['Z'].get('1.0', 'end')
        n_pts  = params['n_pts'].get('1.0', 'end')
        method = params['method'].get()
        
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
        
        self.log(f'Starting hopping mode {expt_type} scan')
        z = z_max
        self.log(f'Starting approach curves from {height}')
        for i, (x, y) in enumerate(points):
            curr_x, curr_y, curr_z = self.Piezo.measure_loc()
            if i != 0:
                self.Piezo.retract(height=10, speed=1, relative=True)
            # time.sleep(0.3)
            self.Piezo.goto(x, y, z_max) # retract
            time.sleep(0.3)
            if self.master.ABORT:
                self.log('Hopping mode aborted')
                return
            if not self.master.TEST_MODE:
                z, _ = self.approach(start_coords = (x, y, z_max))
            
            # TODO: run variable echem experiment(s) at each pt
            data = self.run_echems('CV', expt, (x, y, z), i)
                
            grid_i, grid_j = order[i]  
            expt.set_datapoint( (grid_i, grid_j), data)
            
            # Send data for plotting
            self.master.Plotter.update_heatmap()
            
            expt.save()
            time.sleep(0.01)
        
        self.Piezo.goto(curr_x, curr_y, z_max)
        self.master.expt = expt
            
        return 

    


