import numpy as np
from utils.utils import run, Logger
import serial
import time

PIEZO_COMPORT = 'COM7'

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
        self._stop_monitoring = False
        
        if not self.master.TEST_MODE:
            self.setup_piezo()
    
    
    def stop(self):
        if not hasattr(self, 'port'):
            return
        self.stop_monitoring()
        self.port.close()
        self.log('Serial port closed')
    
    
    def write_and_read(self, msg):
        if not self._piezo_on:
            self.log(f'Piezo not on! Could not send message: {msg}', quiet=True)
            return
        self.port.write(f'{msg}\r'.encode('utf-8'))
        time.sleep(0.1)
        r = self.port.read_all()
        if r:
            self.log(r)
    
    
    def write(self, msg):
        if not self._piezo_on:
            return
        self.port.write(f'{msg}\r'.encode('utf-8'))
        # r = self.port.read_all()
        # if r:
        #     self.log(r)
    
        
    def setup_piezo(self):
        try:
            self.port = serial.Serial(PIEZO_COMPORT, timeout=0.5,
                                  baudrate=19200,
                                  xonxoff=True)
        except Exception as e:
            print(f"Error opening piezo port: {e}")
            return
        self._piezo_on = True
        
        # Set all channels to remote control only
        self.write_and_read('setk,0,1')
        self.write_and_read('setk,1,1')
        self.write_and_read('setk,2,1')
        
        # Set to closed loop
        self.write_and_read('cloop,0,1')
        self.write_and_read('cloop,1,1')
        self.write_and_read('cloop,2,1')
        
        # Output actuator position instead of voltage
        self.write_and_read('monwpa,0,1')
        
        self.log('Setup complete')
        self.start_monitoring()
   
   
    def start_monitoring(self):
        run(self.position_monitor)
        
    def stop_monitoring(self):
        self._stop_monitoring = True
   
    def position_monitor(self):
        '''
        Called in its own thread. 
        '''
        while True:
            if self._stop_monitoring:
                self._stop_monitoring = False
                return
            self.x, self.y, self.z = self.measure_loc()
            time.sleep(0.5)
            
        
        
    def measure_loc(self):
        if not self._piezo_on:
            return (-1,-1,-1)
        self.port.read_all()
        self.write('measure')
        time.sleep(0.01)
        # output from controller terminates with '\r'
        location = self.port.read_until(b'\r').decode('utf-8')
        _, x, y, z = location.strip('\r').split(',')
        return x, y, z
        
    
    # Return current (software) x,y,z
    # TODO: measure every time?
    def loc(self):
        return (self.x, self.y, self.z)
    
    
    # Send piezo to (x,y,z)
    # TODO: measure loc after setting?
    def goto(self, x, y, z):
        if self._piezo_on:
            self.write(f'setall,{x},{y},{z}')
            self.x, self.y, self.z = x, y, z
        self.x, self.y, self.z = self.measure_loc()
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
        

    
    
if __name__ == '__main__':
    class thismaster():
        def __init__(self):
            self.register = lambda x:0
            self.TEST_MODE = True
            
    master = thismaster()
    piezo = Piezo(master)
    piezo.setup_piezo()
