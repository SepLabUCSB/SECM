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
    
    def set_new_scan_bounds(self, corners):
        # i.e. [(5, 5), (5, 44), (44, 5), (44, 44)]
        corners.sort()
        self.starting_coords = corners[0]
        scale = corners[2][0] - corners[0][0]
        print(f"starting coords: {self.starting_coords}")
        return scale
    
    def zero(self):
        self.starting_coords = (0,0)
        self.goto(0,0, self.z)
    

    
if __name__ == '__main__':
    # grid testing
    points = []
    order  = []
    coords = np.linspace(0,1,9)
    cnt = 0
    reverse = False
    for j, y in reversed(list(enumerate(coords))):
        s = ''
        o = ''
        if reverse:
            for i, x in reversed(list(enumerate(coords))):
                points.append((x,y))
                order.append((i,j))
                s = f'({x:.1f}, {y:.1f}) ' + s
                o = f'{str(cnt).rjust(3)} ' + o
                cnt += 1
            reverse = False
        else:
            for i, x in enumerate(coords):
                points.append((x,y))
                order.append((i,j))
                s += f'({x:.1f}, {y:.1f}) '
                o += f'{str(cnt).rjust(3)} '
                cnt += 1
            reverse = True
