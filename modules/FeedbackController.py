import numpy as np
import time
import datetime
from utils.utils import run
from modules.DataStorage import Experiment, DataPoint


def get_xy_coords(length, n_points):
        # Generate ordered list of xy coordinates for a scan
        # ----->
        # <-----
        # ----->
        points = []
        order  = []
        coords = np.linspace(0, length, n_points)
        
        reverse = False
        i, j = 0, 0 # i -> x, j -> y
        for x in coords:
            if reverse:
                for j, y in reversed(list(enumerate(coords))):
                    points.append((x,y))
                    order.append((i,j))
                reverse = False
                i += 1
            else:
                for j, y in enumerate(coords):
                    points.append((x,y))
                    order.append((i,j))
                reverse = True
                i += 1
                
        return points, order




class FeedbackController():
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        # Get local refs to other modules
        self.Piezo = self.master.Piezo
        self.ADC = self.master.ADC
        self.HekaWriter = self.master.HekaWriter

    

    def approach_curve(self, i_cutoff):
        
        # current = self.ADC.get_current()
        current = np.random.rand()
        return current
    
    def CV(self):
        voltage = np.linspace(0, 0.5, 50)
        max_I = 100*np.random.rand()
        current = np.linspace(0, max_I, 50)
        return voltage, current
    
    def hopping_mode(self, params, fig):
        length = params['size'].get('1.0', 'end')
        height = params['Z'].get('1.0', 'end')
        n_pts  = params['n_pts'].get('1.0', 'end')
        method = params['method'].get()
        
        length = float(length) 
        z      = float(height)
        n_pts  = int(n_pts)
        
        points, order = get_xy_coords(length, n_pts)
        
        # Initialize data storage 
        gridpts = np.array([
            np.array([0 for _ in range(n_pts)]) for _ in range(n_pts)
            ], dtype=np.float32)
        
        expt = Experiment(data = gridpts, length = length)
        expt.set_scale(length)
        for i, (x, y) in enumerate(points):
            data = DataPoint(loc = (x,y,0), data = 0.0)
            grid_i, grid_j = order[i]
            expt.set_datapoint( (grid_i, grid_j), data)
                
        self.master.set_expt(expt)
        self.master.Plotter.set_axlim('fig1',
                                      xlim=(0,length),
                                      ylim=(0,length)
                                      )

        for i, (x, y) in enumerate(points):
            if self.master.ABORT:
                self.master.make_ready()
                break
            self.Piezo.goto(x, y, z)
            
            # TODO: run variable echem experiment(s) at each pt
            # I = self.approach_curve(0)
            voltage, current = self.CV()
            
            data = DataPoint(
                    loc = (x,y,z),
                    data = [
                        np.linspace(0,1,len(voltage)),
                        voltage,
                        current
                        ]
                    )
                        
            expt.set_datapoint( (grid_i, grid_j), data)
            
            # Send data for plotting
            self.master.Plotter.data1 = expt.get_heatmap_data()
            
            time.sleep(0.01)
        
        self.master.expt = expt
            
        return 

    


