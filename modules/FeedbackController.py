import numpy as np
import time
from io import StringIO
import os
from utils.utils import run
from modules.DataStorage import Experiment, CVDataPoint




def read_heka_data(file):
    # Use StringIO object to parse through file
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
    




class FeedbackController():
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        # Get local refs to other modules
        self.Piezo = self.master.Piezo
        self.ADC = self.master.ADC
        self.HekaWriter = self.master.HekaWriter

    

    def do_approach_curve(self, i_cutoff):
        
        # current = self.ADC.get_current()
        current = np.random.rand()
        return current
    
    def fake_CV(self, i):
        voltage = np.linspace(0, 0.5, 50)
        max_I = 100*np.random.rand()
        current = np.linspace(0, i, 50)
        return voltage, current
    
    def run_CV(self, save_path, name):
        self.master.HekaWriter.run_CV_loop(save_path=save_path,
                                           name=name)
        output = read_heka_data(
                os.path.join(save_path, f'{name}.asc')
                                )
        _, t, i, _, v = output
        return v, i
        
    
    
    def hopping_mode(self, params, expt_type='CV'):
        length = params['size'].get('1.0', 'end')
        height = params['Z'].get('1.0', 'end')
        n_pts  = params['n_pts'].get('1.0', 'end')
        method = params['method'].get()
        
        length = float(length) 
        z      = float(height)
        n_pts  = int(n_pts)
        
        
        # Setup potentiostat for experiment
        if expt_type == 'CV':
            
            if not self.master.TEST_MODE:
                self.master.GUI.set_amplifier()
                CV_vals = self.master.GUI.get_CV_params()
                self.master.HekaWriter.setup_CV(*CV_vals)
        
        
        # Initialize data storage 
        expt = Experiment(length    = length,
                          n_pts     = n_pts,
                          expt_type = expt_type)
        points, order = expt.get_xy_coords()     
        
        self.master.set_expt(expt)
        self.master.Plotter.set_axlim('fig1',
                                      xlim=(0,length),
                                      ylim=(0,length)
                                      )
        
        
        for i, (x, y) in enumerate(points):
            if self.master.ABORT:
                return
            self.Piezo.goto(x, y, z)
            
            # TODO: run variable echem experiment(s) at each pt
            if self.master.TEST_MODE:
                voltage, current = self.fake_CV(i)
            else:
                voltage, current = self.run_CV(expt.path, i)
            
            data = CVDataPoint(
                    loc = (x,y,z),
                    data = [
                        np.linspace(0,1,len(voltage)),
                        voltage,
                        current
                        ]
                    )
            
            grid_i, grid_j = order[i]            
            expt.set_datapoint( (grid_i, grid_j), data)
            
            # Send data for plotting
            self.master.Plotter.data1 = expt.get_heatmap_data()
            expt.save()
            time.sleep(0.01)
        
        self.master.expt = expt
            
        return 

    


