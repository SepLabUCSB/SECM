from datetime import datetime
import os
import pickle
import numpy as np


def nearest(arr, val):
    diff = abs(np.array(arr) - val)
    idx = np.where(diff == min(diff))[0][0]
    return idx, arr[idx]


def get_xy_coords(length, n_pts):
        # Generate ordered list of xy coordinates for a scan
        # ----->
        # <-----
        # ----->
        # !!!          NOW DONE BY PIEZO CLASS       !!!
        # !!! ONLY HERE FOR DEFAULT EXPERIMENT INIT  !!!
        points = []
        order  = []
        coords = np.linspace(0, length, n_pts)
        
        reverse = False
        # i, j = 0, 0 # i -> x, j -> y
        for i, y in enumerate(coords):
            if reverse:
                for j, x in reversed(list(enumerate(coords))):
                    points.append((x,y))
                    order.append((i,j))
                reverse = False
            else:
                for j, x in enumerate(coords):
                    points.append((x,y))
                    order.append((i,j))
                reverse = True
            # j += 1
        
        return points, order


class Experiment:
    '''
    Structure for storing SECM data.
    
    self.data is a n x n array representing the scanning region.
    
    Each entry in the array is a DataPoint type object. It has
    attributes DataPoint.loc, which is its location in piezo coordinates,
    and DataPoint.data, which may be a float, list, or array depending on
    what type of electrochemical data that point represents. 
    '''
    
    
    def __init__(self, points:list=list(), order:list=list(),                 
                 expt_type='', path='D:/SECM/temp/temp.secmdata'):
        if not os.path.exists(path.split('/')[0]):
            path = 'temp/temp.secmdata'
        self.timestamp  = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        self.path       = path
        self.basepath   = '/'.join(path.split('/')[:-1])
        os.makedirs(self.basepath, exist_ok=True)
        
        # Set blank SECM grid data
        self.set_type(expt_type)
        self.setup_blank(points, order)
        self.saved = True # Toggles to False when first data point is appended
    
    
    def isSaved(self):
        return self.saved
    
    
    def save(self, path=None):
        if not path:
            path = self.path
        
        if not path.endswith('.secmdata'):
            path += '.secmdata'
                
        with open(path, 'wb') as f:
            # json.dump(d, f)
            pickle.dump(self, f)
        if not path.endswith('temp.secmdata'):
            print(f'Saved as {path}')
            self.saved = True
    
    
    def setup_blank(self, points, order):
        if len(points) == 0:
            points, order = get_xy_coords(length=10, n_pts=10)
        
        n_pts = int(np.sqrt(len(points)))
        xs = [x for (x,y) in points]
        length = max(xs) - min(xs)
        
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
        
        self.set_scale(length)
        return
    
    
    def get_xy_coords(self):
        return self.points, self.order
    
    
    def set_type(self, expt_type):
        self.expt_type = expt_type
        self.saved = False
    
    
    def set_scale(self, length):
        self.length = length  
        self.saved = False
    
        
    def set_datapoint(self, grid_ids, point):
        i, j = grid_ids[0], grid_ids[1]
        self.data[j][i] = point  # TODO: heatmap axes are messed up?
        self.saved = False
        
        
    def get_data(self):
        # self.datapoints.sort(key=lambda p:(p.loc[0], p.loc[1]))
        return {
            'length': self.length,
            'data': self.data.tolist(),
            'timestamp':self.timestamp,
            }
    
    def get_heatmap_data(self, datatype='max', arg=None):
        '''
        datatype: string, specifies what data to return
        arg: string or float to accompany datatype
        '''
        gridpts = np.array([
            [d.get_val(datatype, arg) for d in row]
            for row in self.data]         
            )
        return gridpts
    
    def get_loc_data(self):
        gridpts = np.array([
            [(float(d.loc[0]), float(d.loc[1])) for d in row]
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
        idx = 0
        for i, datapoint in enumerate(self.data.flatten()):
            x0, y0, z0 = datapoint.loc
            distance = np.sqrt(
                                (x - x0)**2 + (y - y0)**2 
                                )
            if distance < min_dist:
                min_dist = distance
                closest = datapoint
                idx = i
        return idx, closest
    
  
    
# Base DataPoint class
class DataPoint:
    # Data from a single SECM pixel
    def __init__(self, loc: tuple, data):
        self.loc      = loc
        # self.data accepted types:
        #  * float: single potential measurements
        #  * list: CV: [ [t], [V], [I] ]
        self.data = data
        self.gain = 1 # Used for ADCDataPoint
    
        
    def get_val(self, datatype='max', arg=None):
        # Return requested value (for heatmap display)
        # Overwrite in subclasses
        if datatype == 'z':
            return self.loc[2]
        return self.data
    
    def get_data(self):
        # Return all data
        return self.data    


class ADCDataPoint(DataPoint):
    
    def append_data(self, t, V, I):
        try:
            self.data[0].extend(t)
            self.data[1].extend(V)
            self.data[2].extend(I)
        except TypeError: #passed floats instead of lists
            self.data[0].append(t)
            self.data[1].append(V)
            self.data[2].append(I)
        return     

    def set_HEKA_gain(self, gain):
        self.gain = gain
        
    def reset_times(self):
        # Saved time data is not precise because data is send to the host
        # PC in blocks and the time of each datapoint is backcalculated after.
        # These data aren't quite evenly spaced (at 10kHz sampling, spacing
        # between points is 100 +- 18 us), so use this function to reset the
        # stored time data to be evenly spaced.
        self.data[0] = list(np.linspace(self.data[0][0], 
                                        self.data[0][-1],
                                        len(self.data[1])
                                        )
                            )
        

        

class SinglePoint(DataPoint):
    def get_val(self, datatype=None, arg=None):
        if datatype == 'z':
            return self.loc[2]
        return self.data



class CVDataPoint(DataPoint):
    def get_val(self, datatype='max', arg=None):
        '''
        valtype: str, defines what to return
            'max': max I
            'avg': avg I
            'val_at': I at valarg voltage
            etc
        '''
        if datatype == 'z':
            return self.loc[2]
        if datatype=='max':
            return max(self.data[2])
        if datatype=='loc':
            return self.loc[0] + self.loc[1]
        if datatype == 'avg':
            return np.mean(self.data[2])
        if datatype == 'val_at':
            idx, _ = nearest(self.data[1], arg)
            return self.data[2][idx]
    
    def get_data(self):
        return self.data
    
    



def load_from_file(path):
    with open(path, 'rb') as f:
        expt = pickle.load(f)
        return expt
    #     d = json.load(f)
    # return Experiment(data=d['data'], length=d['length'])



