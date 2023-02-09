from datetime import datetime
import os
import pickle
import numpy as np


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
        for y in reversed(coords):
            if reverse:
                for j, x in reversed(list(enumerate(coords))):
                    points.append((x,y))
                    order.append((i,j))
                reverse = False
                i += 1
            else:
                for j, x in enumerate(coords):
                    points.append((x,y))
                    order.append((i,j))
                reverse = True
                i += 1
                          
        return points, order


class Experiment:
    
    def __init__(self, length=10, n_pts=10, expt_type='', 
                 path='D:/SECM/temp.secmdata'):
        if not os.path.exists(path.split('/')[0]):
            path = 'temp/temp.secmdata'
        self.timestamp  = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        self.path       = path
        self.basepath   = '/'.join(path.split('/')[:-1])
        os.makedirs(self.basepath, exist_ok=True)
        
        # Set blank SECM grid data
        self.set_scale(length)
        self.set_type(expt_type)
        self.setup_blank(length, n_pts)
    
    
    def setup_blank(self, length, n_pts):
        points, order = get_xy_coords(length, n_pts)
        
        gridpts = np.array([
            np.array([0 for _ in range(n_pts)]) for _ in range(n_pts)
            ], dtype=object)
        
        self.points = points
        self.order  = order
        self.data   = gridpts
        
        for i, (x, y) in enumerate(points):
            data = SinglePoint(loc = (x,y,0), data = 0)
            grid_i, grid_j = order[i]
            self.set_datapoint( (grid_i, grid_j), data)
        return
    
    
    def get_xy_coords(self):
        return self.points, self.order
    
    
    def set_type(self, expt_type):
        self.expt_type = expt_type
    
    
    def set_scale(self, length):
        self.length = length
    
        
    def set_datapoint(self, grid_ids, point):
        i, j = grid_ids[0], grid_ids[1]
        self.data[i][j] = point
        
        
    def get_data(self):
        # self.datapoints.sort(key=lambda p:(p.loc[0], p.loc[1]))
        return {
            'length': self.length,
            'data': self.data.tolist(),
            'timestamp':self.timestamp,
            }
    
    def get_heatmap_data(self):
        gridpts = np.array([
            [d.get_val() for d in row]
            for row in self.data]         
            )
        return gridpts
    
    def get_loc_data(self):
        gridpts = np.array([
            [(int(d.loc[0]), int(d.loc[1])) for d in row]
            for row in self.data]         
            )
        return gridpts
    
    
    def get_nearest_datapoint(self, x, y):
        '''
        Returns DataPoint object with location nearest to the 
        requested (x, y) coordinates
        '''
        min_dist = 1e10
        closest  = None
        for datapoint in self.data.flatten():
            x0, y0, z0 = datapoint.loc
            distance = np.sqrt(
                                (x - x0)**2 + (y - y0)**2 
                                )
            if distance < min_dist:
                min_dist = distance
                closest = datapoint
        return closest
    
    
    def save(self, path=None):
        if not path:
            path = self.path
        
        if not path.endswith('.secmdata'):
            path += '.secmdata'
                
        with open(path, 'wb') as f:
            # json.dump(d, f)
            pickle.dump(self, f)
        print(f'Saved as {path}')
            

    


class DataPoint:
    # Data from a single SECM pixel
    def __init__(self, loc: tuple, data):
        self.loc      = loc
        # self.data accepted types:
        #  * float: single potential measurements
        #  * list: CV: [ [t], [V], [I] ]
        self.data = data
        
    def get_val(self, valtype='max', valarg=None):
        # Overwrite in subclasses
        return self.data
    
    def get_data(self):
        return [0], [0], [0]

        

class SinglePoint(DataPoint):
    def get_val(self):
        return self.data



class CVDataPoint(DataPoint):
    def get_val(self, valtype='max', valarg=None):
        '''
        valtype: str, defines what to return
            'max': max I
            'avg': avg I
            'val_at': I at valarg voltage
            etc
        '''
        if valtype=='max':
            return max(self.data[2])
    
    def get_data(self):
        return self.data
    
    



def load_from_file(path):
    with open(path, 'rb') as f:
        expt = pickle.load(f)
        return expt
    #     d = json.load(f)
    # return Experiment(data=d['data'], length=d['length'])



