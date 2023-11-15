from datetime import datetime
from io import StringIO
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
        self.settings = None
    
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
            
            
    def save_settings(self, settings):
        self.settings = settings
    
    
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
    
    
    def get_nearest_datapoint(self, x, y, pt_idx=0):
        '''
        Returns DataPoint object with location nearest to the 
        requested (x, y) coordinates.
        
        If the object is a PointsList, return PointsList[idx]
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
        # if isinstance(closest, PointsList):
        #     closest = closest[pt_idx]
            
        return idx, closest
    
    
    def do_analysis(self, analysis_func, *args):
        '''
        Runs a function on each DataPoint in this experiment.
        Function should return a modified DataPoint with an attribute
        DataPoint.analysis = {(analysis_func, *args):value}
        
        This dictionary is accessed by the heatmap plotter to draw the point's color
        
        Any additional elements to draw on the echem (right) figure can be
        added as matplotlib.artist.Artist objects to the list DataPoint.artists
        
        analysis_func: function to apply to each point
        args: arguments to pass to analysis_func
        '''
        for i, row in enumerate(self.data):
            for j, pt in enumerate(row):
                if isinstance(pt, PointsList):
                    for k, subpt in enumerate(pt.data):
                        if isinstance(subpt, CVDataPoint):
                            pt.data[k] = analysis_func(subpt, *args)
                            break
                    if not hasattr(pt, 'analysis'):
                        pt.analysis = {}
                    pt.analysis[(analysis_func, *args)] = pt.data[k].analysis[(analysis_func, *args)]
                    self.data[i][j] = pt
                else:
                    self.data[i][j] = analysis_func(pt, *args)
                    
        gridpts = np.array([
            [pt.analysis[(analysis_func, *args)] for pt in row]
            for row in self.data]         
            )
        
        return gridpts
    
    
    def max_points_per_loc(self):
        '''
        Checks all DataPoints in this experiment. Returns the length of
        the longest PointsList
        '''
        longest = 1
        for row in self.data:
            for pt in row:
                if isinstance(pt, PointsList):
                    if len(pt.data) > longest:
                        longest = len(pt.data)
        return longest
    
    
    def save_to_folder(self, path):
        '''
        Export all data to the specified path
        '''
        os.makedirs(path, exist_ok = True)
        for j, row in enumerate(self.data):
            for i, pt in enumerate(row):
                if isinstance(pt, SinglePoint): 
                    continue
                if isinstance(pt, PointsList):
                    for point in pt.points:
                        fname = os.path.join(path, 
                                             f'{i:02}_{j:02}_{str(pt)}.asc')
                        pt.save(path=fname)
                    continue
                fname = os.path.join(path, f'{i:02}_{j:02}_{str(pt)}.asc')
                pt.save(path=fname)
    
  
    
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
        
    def __str__(self):
        return 'DataPoint'
    
        
    def get_val(self, datatype='max', arg=None):
        # Return requested value (for heatmap display)
        # Overwrite in subclasses
        if datatype == 'z':
            return self.loc[2]
        return self.data
    
    def get_data(self):
        # Return all data
        return self.data  
    
    def save(self, path):
        # Write contents of self to given path
        with open(path, 'w') as f:
            x, y, z = self.loc
            f.write(f'xyz (um):\n')
            f.write(f'{x:0.3f}\t{y:0.3f}\t{z:0.3f}\n')
        self._save(path)
    
    def _save(self, path):
        # Overwrite in subclasses
        pass
            


class ADCDataPoint(DataPoint):
    
    def __str__(self):
        return 'ADCDataPoint'
    
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

    def get_data(self, n=None):
        '''
        n: int, optional. Return last n data points
        '''
        if n:
            return [l[-n:] for l in self.data]
        return self.data

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
    
    def __str__(self):
        return 'SinglePoint'
    
    def get_val(self, datatype=None, arg=None):
        if datatype == 'z':
            return self.loc[2]
        return self.data
    
    def _save(self, path):
        # Don't save data of this type 
        # (used as placeholder in scanning grid)
        pass



class CVDataPoint(DataPoint):   
          
    def __str__(self):
        return 'CVDataPoint'  
    
    def get_val(self, datatype='max', arg=None):
        '''
        valtype: str, defines what to return
            'max': max I
            'avg': avg I
            'val_at': I at valarg voltage
            etc
        '''
        if datatype == 'z':
            # Handle early bug in some saved data
            if type(self.loc[2]) == tuple:
                return self.loc[2][0]
            return self.loc[2]
        if datatype=='max':
            return max(self.data[2])
        if datatype=='loc':
            return self.loc[0] + self.loc[1]
        if datatype == 'avg':
            return np.mean(self.data[2])
        if datatype == 'val_at':
            # Return value from first, forward sweep
            
            idx    = 0
            delta  = 1e6
            deltas = []
            # TODO: make this faster?
            for i, v in enumerate(self.data[1]):
                deltas.append(abs(v - arg))
                if abs(v - arg) < delta:
                    # Getting closer
                    idx = i
                    delta = abs(v - arg)
                    continue
                if len(deltas) < 5:
                    continue
                if all([deltas[-1] > deltas[j] for j in [-2,-3,-4,-5,-6]]):
                    # Getting farther away from value. Return what we have
                    return self.data[2][idx]
            return self.data[2][idx]
        if datatype == 'val_at_t':
            idx, _ = nearest(self.data[0], arg)
            return self.data[2][idx]
    
    def get_data(self):
        return self.data
    
    def _save(self, path):
        with open(path, 'a') as f:
            f.write('t/s,E/V,I/A\n')
            for t, V, I in zip(self.data[0], self.data[1], self.data[2]):
                f.write(f'{t},{V},{I}\n')
    

    
class EISDataPoint(DataPoint):    
    def __init__(self, loc: tuple, data:list, applied_freqs:list,
                 corrections: list=None, input_FT_data=False):
        self.loc      = loc
        self.data     = data
        self.applied_freqs = applied_freqs     # Recorded by HekaWriter
        self.corrections   = corrections       # Recorded by HekaWriter
        if not input_FT_data:
            self.FT() # do the Fourier transform
        
    def __str__(self):
        return 'EISDataPoint'
    
        
    def FT(self):
        t, V, I = self.data
        srate = 1/np.mean(np.diff(t))
        
        # Fourier transform
        freqs = srate*np.fft.rfftfreq(len(V))[1:]
        ft_V  = np.fft.rfft(V)[1:]
        ft_I  = np.fft.rfft(I)[1:]
        
        if self.applied_freqs is not None:
            idxs = []
            for f in self.applied_freqs:
                idx, _ = nearest(freqs, f)
                idxs.append(idx)
        else:
            idxs = [i for i, v in enumerate(abs(ft_V)) if v > 0.5]
        
        # Remove all frequencies not in perturbation signal
        freqs = freqs[idxs]
        ft_V  = ft_V[idxs]
        ft_I  = ft_I[idxs]
        Z = ft_V/ft_I
        
        if self.corrections is not None:
            '''
            Correct for filter effects.
            Corrected |Z| = |Z| / Z_corrections
            Corrected  p  =  p  - phase_corrections
            Corrected  Z  = |Z| * exp(1j * phase * pi/180)
            '''
            fs, Z_corrections, phase_corrections = zip(*self.corrections)
            modZ  = np.abs(Z)
            phase = np.angle(Z, deg=True)
            modZ  /= Z_corrections
            phase -= phase_corrections
            Z = modZ * np.exp(1j * phase * np.pi/180)
        
        # Re-save as self.data
        self.data = [freqs, ft_V, ft_I, Z]
        
    def get_val(self, datatype='max', arg=None):
        if datatype == 'z':
            return self.loc[2]
        if datatype == 'val_at':
            idx, _ = nearest(self.data[0], arg)
            return abs(self.data[1][idx])
        else:
            return 0
        
    
        
    def _save(self, path):
        with open(path, 'a') as f:
            f.write("<Frequency>\t<Re(Z)>\t<Im(Z)>\n")
            for freq, Z in zip(self.data[0], self.data[3]):
                f.write(f'{freq}\t{np.real(Z)}\t{np.imag(Z)}\n')
        

class PointsList():
    '''
    Wraps a standard list of DataPoint objects with some helpful extra functions
    
    Overwites all DataPoint methods so it can be used cleanly in place of a DataPoint
    object. By default, returns the appropriate value from the first DataPoint
    in the PointsList.
    '''
    def __init__(self, loc:tuple, data:list):
        '''
        data: list of DataPoint type objects
        '''
        self.loc    = loc
        self.data   = data
        
    def __getitem__(self, i):
        try:
            return self.data[i]
        except IndexError:
            print(f'Invalid index: no {i}-th point. This spot has {len(self.points)} data points')
        except:
            print(f'Invalid index: {i}')
        return self.data[0]
        
    def __str__(self):
        return 'PointsList'
        
    def add_point(self, DataPoint):
        self.data.append(DataPoint)
        
    
    ### DataPoint method overwrites ###
    def get_val(self, datatype='max', arg=None, idx=0):
        return self[idx].get_val(datatype, arg)
    
    def get_data(self, idx=0, **kwargs):
        return self[idx].get_data(**kwargs)
    
    def save(self, path, idx=0):
        return self[idx].save(path)
    
    
    
    



def load_from_file(path):
    with open(path, 'rb') as f:
        expt = pickle.load(f)
        return expt
    #     d = json.load(f)
    # return Experiment(data=d['data'], length=d['length'])



    
        
        
    
    
    
    
    
