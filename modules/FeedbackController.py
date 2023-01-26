import numpy as np
import time
import asyncio
import matplotlib.pyplot as plt
from utils.utils import run


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
    
    def hopping_mode(self, params, fig):
        
        length = params['size'].get('1.0', 'end')
        height = params['Z'].get('1.0', 'end')
        n_pts  = params['n_pts'].get('1.0', 'end')
        
        length = float(length) 
        height = float(height)
        n_pts  = int(n_pts)
        
        points, order = get_xy_coords(length, n_pts)
        
        # Setup figure, need blitting to plot fast enough
        gridpts = np.array([
            np.array([0 for _ in range(n_pts)]) for _ in range(n_pts)
            ], dtype=np.float32)
        
        self.master.Plotter.set_axlim('fig1',
                                      xlim=(0,length),
                                      ylim=(0,length)
                                      )
        
        for i, (x, y) in enumerate(points):
            if self.master.ABORT:
                self.master.make_ready()
                return
            self.Piezo.goto(x, y, height)
            
            # TODO: run variable echem experiment(s) at each pt
            I = self.approach_curve(0)
            
            grid_i, grid_j = order[i]
            gridpts[grid_i][grid_j] = I
            
            # Send data for plotting
            self.master.Plotter.data1 = gridpts
            
            time.sleep(0.01)
        
        
        return

    


