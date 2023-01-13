import numpy as np



class piezoController():
    
    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0
        pass
    
    def loc(self):
        return (self.x, self.y, self.z)
    
    def goto(self, x, y, z):
        self.x, self.y, self.z = x, y, z
        return self.loc()
    
    def get_xy_coords(self, length, n_points):
        points = []
        coords = np.linspace(0, length, n_points)
        
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
    
    def approach(self, step, threshold):

        while True:
            current = readHekaCurrent()
            if current > threshold:
                break
            
            self.goto(self.x, self.y, self.z - step)
        
        return self.z