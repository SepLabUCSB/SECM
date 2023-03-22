import numpy as np
from utils.utils import Logger
import pyvisa



class Piezo(Logger):
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        self.x = 0
        self.y = 0
        self.z = 50
        self.starting_coords = (0,0)
        self._piezo_on = False
        
        if not self.master.TEST_MODE:
            self.setup_piezo()
     
        
    def setup_piezo(self):
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(CONTROLLER_ADDRESS)
        
        # Set all channels to remote control only
        self.inst.write('setk,0,1')
        self.inst.write('setk,1,1')
        self.inst.write('setk,2,2')
        
        # Set to closed loop
        self.inst.write('cloop,0,1')
        self.inst.write('cloop,1,1')
        self.inst.write('cloop,2,1')
        
        # Output actuator position instead of voltage
        self.inst.write('monwpa,0,1')
        
        self._piezo_on = True
        
    
    # Read (x,y,z) from piezo
    def measure_loc(self):
        if not self._piezo_on:
            return
        location = self.inst.query('measure')
        _, x, y, z = location.split(',')
        
    
    # Return current (software) x,y,z
    # TODO: measure every time?
    def loc(self):
        return (self.x, self.y, self.z)
    
    
    # Send piezo to (x,y,z)
    # TODO: measure loc after setting?
    def goto(self, x, y, z):
        if self._piezo_on:
            self.inst.write(f'setall,{x},{y},{z}')
        self.x, self.y, self.z = x, y, z
        return self.loc()
    
    
    
    def get_xy_coords(self, length, n_points):
        # Generate ordered list of xy coordinates for a scan
        # ----->
        # <-----
        # ----->
        points = []
        order  = []
        coords = np.linspace(self.starting_coords[0], 
                             self.starting_coords[0] + length, 
                             n_points)
        
        reverse = False
        cnt = 0
        for j, y in reversed(list(enumerate(coords))):
            s = ''
            o = ''
            
            if reverse:
                for i, x in reversed(list(enumerate(coords))):
                    points.append((x,y))
                    order.append((i,j))
                    # s = f'({x:0.0f}, {y:0.0f}) ' + s
                    s = f'{str(cnt).ljust(3)} ' + s
                    o = f'({i}, {j}) ' + o
                    cnt += 1
                reverse = False
            else:
                for i, x in enumerate(coords):
                    points.append((x,y))
                    order.append((i,j))
                    o += f'({i}, {j}) '
                    s += f'{str(cnt).ljust(3)} '
                    # s += f'({x:0.0f}, {y:0.0f}) '
                    cnt += 1
                reverse = True
            # print(s)
        
        return points, order
    
    
    # When zooming in to a new region, set new starting coordinates
    # for the scan (otherwise always starts from 0,0)
    def set_new_scan_bounds(self, corners):
        # i.e. [(5, 5), (5, 44), (44, 5), (44, 44)]
        corners.sort()
        self.starting_coords = corners[0]
        scale = corners[2][0] - corners[0][0]
        print(f"starting coords: {self.starting_coords}")
        return scale
    
    
    # Reset to (0,0)
    def zero(self):
        self.starting_coords = (0,0)
        self.goto(0,0, self.z)
    
