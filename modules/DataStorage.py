from dataclasses import dataclass
from datetime import datetime
import json
import numpy as np




class Experiment:
    
    def __init__(self, data, length=10, exp_type='', path='temp.json'):
        self.timestamp  = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        self.exp_type   = ''
        self.path       = path
        
        self.data   = np.array(data, dtype=object)
        self.length = length # scale of SECM grid in um
        
    
    
    def set_exp_type(self, exp_type):
        self.exp_type = exp_type
    
    def set_scale(self, length):
        self.length = length
    
    # def append(self, loc, data):
    #     self.append_datapoint( DataPoint(loc, data) )
    
    
    # def append_datapoint(self, point):
    #     self.datapoints.append(point)
    
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
    
    
    def save(self, path=None):
        if path: 
            self.path = path
            
        d = self.get_data()
        
        with open(self.path, 'w') as f:
            json.dump(d, f)
            

    


class DataPoint:
    # Data from a single SECM pixel
    def __init__(self, loc: tuple, data):
        self.loc      = loc
        # self.data accepted types:
        #  * float: single potential measurements
        #  * list: CV: [ [t], [V], [I] ]
        self.data = data
        
    def get_val(self, valtype='max', valarg=None):
        '''
        valtype: str, defines what to return
            'max': max I
            'avg': avg I
            'val_at': I at valarg voltage
            etc
        '''
        if type(self.data) == float:
            return self.data
        elif valtype=='max':
            return max(self.data[2])
    



def load_from_file(path):
    with open(path, 'r') as f:
        d = json.load(f)
    return Experiment(data=d['data'], length=d['length'])



