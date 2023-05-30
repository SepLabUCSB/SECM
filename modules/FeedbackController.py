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

    
    def approach(self, i_cutoff:float, voltage:float, start_coords:tuple=None):
        '''
        start_coords: (x,y,z)
        voltage: float, mV
        i_cutoff: float, A
        
        Step probe closer to surface starting at point (x,y,z). 
        Stop when measured i > i_cutoff
        '''
        
        j = 0
        step = 0.5 # um
        if not start_coords:
            start_coords = self.Piezo.loc()
        x, y, z_start = start_coords
        x, y, z_start = 0, 0, 80
        self.Piezo.goto(x, y, z_start)
        self.HekaWriter.macro(f'E Vhold {voltage}')
        gain = 1e9 * self.master.GUI.amp_params['float_gain']
        run(partial(self.ADC.polling, 60))
        time.sleep(0.2)
        for j in range(200):
            if self.master.ABORT:
                break
            z = z_start - j*step
            if z < 0:
                break
            self.Piezo.goto(x, y, z)
            # Collect some data at this loc
            time.sleep(0.1)
            t, V, I = self.ADC.pollingdata.get_data()
            I = np.array(I)
            I /= gain # convert V -> I
            val = np.average(abs(I[-20:]))
            if val > i_cutoff:
                break 
        self.ADC.STOP_POLLING()  
        return z


    def do_approach_curve(self, i_cutoff):
        
        # current = self.ADC.get_current()
        current = np.random.rand()
        return current
    
    
    def fake_CV(self, i):
        # Generate fake data for testing piezo
        voltage = np.linspace(0, 0.5, 50)
        max_I = 100*np.random.rand()
        current = np.linspace(0, i, 50)
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
            return
        if expt_type == 'CV':
            self.master.GUI.set_amplifier()
            CV_vals = self.master.GUI.get_CV_params()
            self.master.HekaWriter.setup_CV(*CV_vals)
        return
    
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
        self.potentiostat_setup(expt_type)
                                
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
        for i, (x, y) in enumerate(points):
            if self.master.ABORT:
                self.log('Hopping mode aborted')
                self.master.make_ready()
                return
            if not self.master.TEST_MODE:
                self.Piezo.goto(x, y, z_max)
                # z = self.approach()
            
            # TODO: run variable echem experiment(s) at each pt
            data = self.run_echems('CV', expt, (x, y, z), i)
                
            grid_i, grid_j = order[i]  
            expt.set_datapoint( (grid_i, grid_j), data)
            
            # Send data for plotting
            self.master.Plotter.update_heatmap()
            
            expt.save()
            time.sleep(0.01)
        
        self.master.expt = expt
            
        return 

    


