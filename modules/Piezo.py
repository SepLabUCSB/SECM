import numpy as np
from utils.utils import Logger



class Piezo(Logger):
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        self.x = 0
        self.y = 0
        self.z = 0
        self.starting_coords = (0,0)
        pass
    
    def loc(self):
        return (self.x, self.y, self.z)
    
    def goto(self, x, y, z):
        self.x, self.y, self.z = x, y, z
        return self.loc()
    
    def get_xy_coords(self, length, n_points):
        # Generate ordered list of xy coordinates for a scan
        # ----->
        # <-----
        # ----->
        points = []
        coords = np.linspace(self.starting_coords[0], length, n_points)
        
        reverse = False
        for x in coords:
            if reverse:
                for y in reversed(coords):
                    points.append((x,y))
                reverse = False
            else:
                for y in coords:
                    points.append((x,y))
                reverse = True
        return points
    
    def set_new_scan_bounds(self, corners):
        # i.e. [(5, 5), (5, 44), (44, 5), (44, 44)]
        corners.sort()
        self.starting_coords = corners[0]
        scale = corners[2][0] - corners[0][0]
        return scale
    
    def zero(self):
        self.starting_coords = (0,0)
        self.goto(0,0, self.z)
    
