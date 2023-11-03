import numpy as np
from ..utils.utils import run, Logger
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
        self.counter = 0
        self._halt = False
        self._piezo_on = False
        self._is_monitoring = False
        self._stop_monitoring = False
        self._moving = False
        
        if not self.master.TEST_MODE:
            self.setup_piezo()
    
    
    def isMoving(self):
        return self._moving
    
    
    def stop(self):
        if not hasattr(self, 'port'):
            return
        self.stop_monitoring()
        self.port.close()
        self.log('Serial port closed')
        self._piezo_on = False
    
    
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
        # try:
        self.port = serial.Serial(PIEZO_COMPORT, timeout=0.5,
                              baudrate=19200,
                              xonxoff=True)
        # except Exception as e:
        #     print(f"Error opening piezo port: {e}")
        #     return
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
        
        self.goto(0,0,80)
        
        self.log('Setup complete')
        self.start_monitoring()
   
   
    def start_monitoring(self):
        if not self._is_monitoring:
            run(self.position_monitor)
        
    def stop_monitoring(self):
        self._stop_monitoring = True
   
    def position_monitor(self):
        '''
        Called in its own thread. 
        '''
        while True:
            if self.master.ABORT:
                self._is_monitoring = False
                return
            if self._stop_monitoring:
                self._stop_monitoring = False
                self._is_monitoring = False
                return
            self._is_monitoring = True
            self.measure_loc()
            time.sleep(0.5)
            
        
        
    def measure_loc(self):
        if not self._piezo_on:
            return (-1,-1,-1)
        
        # Don't try to measure during movement
        if self._moving:
            return (self.x, self.y, self.z)
        
        self.port.read_all()
        self.write('measure')
        time.sleep(0.001)
        
        # output from controller terminates with '\r'
        location = self.port.read_until(b'\r').decode('utf-8')
        try:
            location = location.split('aw')[1]
            _, x, y, z = location.strip('\r').split(',')
            x, y, z = float(x), float(y), float(z)
            x = 80 - x
            self.x, self.y, self.z = float(x), float(y), float(z)
            return (self.x, self.y, self.z)
        except:
            self.log(f'Error measuring location. Received: {location}')
            return (self.x, self.y, self.z)
        
        
        
    
    # Return current x,y,z
    def loc(self):
        return self.measure_loc()
    
    
    # Send piezo to (x,y,z)
    def goto(self, x, y, z):
        
        x, y, z = float(x), float(y), float(z)
        '''
        Requested coordinates aren't reached accurately. Each channel
        has a different offset which was determined empirically. We
        correct for this offset here so the coordinates we request
        are the coordinates we get
        '''
        
        x = 80 - x   # Piezo has left-hand coordinates, we want right-hand
        
        x = (x + 1.742)*(80/(82.090 + 1.742))
        y = (y + 1.825)*(80/(81.980 + 1.825))
        z = (z + 1.843)*(80/(82.001 + 1.843))
        
        if self._piezo_on:
            cmd = f'setall,{x},{y},{z}'
            self._moving = True
            self.write(cmd)
            self._moving = False
    
    def goto_z(self, z):
        '''
        Set z to the requested value. Doesn't change x or y
        '''
        z = float(z)
        z = (z + 1.843)*(80/(82.001 + 1.843))
        if self._piezo_on:
            cmd = f'set,2,{z}'
            self._moving = True
            self.write(cmd)
            self._moving = False
    
    ########################################
    ######                         #########
    ######         MOVEMENTS       #########
    ######                         #########
    ########################################
        
    def halt(self):
         '''
         Immediately stop current approach/ retract
         '''
         self._halt = True
        
        
    def approach(self, forced_step_size=None):
        '''
        Starting from the current location, reduce Z in small steps at
        the given speed until Z = 0 (or external stop command is received)
        
        speed: float, approach speed in um/s
        forced_step_size: (Optional) float, step size in um. If given, step_size is 
                          prioritized over speed
        '''
        
        step_size  = 0.01            # step size um
        step_delay = 0.001           # step time in s
        
        if forced_step_size:
            step_size = forced_step_size
            step_delay = 0.0001
        
        self.log(f'Running approach curve with step size {step_size} um, dwell time {step_delay} s')
        
        # Stop periodic location checks
        self.stop_monitoring()
        x,y,z = self.measure_loc()
        # st = time.time()
        while z > 0:
            self._moving = True
            if self.master.ABORT:
                break
            if self._halt:
                break
            z -= step_size
            # self.goto(x,y,z)
            self.goto_z(z)
            # print(f'{time.time() - st:0.5f}, {z:0.5f}')
            self.x, self.y, self.z = x,y,z
            time.sleep(step_delay)
        
        self.x, self.y, self.z = self.measure_loc()
        self.counter += 1
        self._halt = False
        self._moving = False
        return
    
    
    def retract(self, height, relative=False):
        '''
        Starting from the current location, increase Z in small steps at
        the given speed until Z = height
        
        If relative == True, instead increase Z until Z = height + starting height
        
        height: float, target z height
        speed: float, retract speed in um/s
        '''
        
        step_size  = 0.01            # step size um
        
        # Stop periodic location checks
        self.stop_monitoring()
        x,y,z = self.measure_loc()
        
        if relative:
            height += z
        
        self.log(f'Retracting to {height}, currently at {z}')
        while z < height:
            self._moving = True
            if self.master.ABORT:
                break
            if self._halt:
                break
            if z > 80:
                break
            z += step_size
            self.goto_z(z)
            # self.goto(x,y,z)
            self.x, self.y, self.z = x,y,z
            time.sleep(0.001)
        
        self.log(f'Finished retracting, current height {z}')
        self.counter += 1
        self._halt = False
        self._moving = False
        self.start_monitoring()
        return z
    
    
    
    ########################################
    ######                         #########
    ######     SCANNING METHODS    #########
    ######                         #########
    ########################################
    
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
    import matplotlib.pyplot as plt
    class thismaster():
        def __init__(self):
            self.register = lambda x:0
            self.TEST_MODE = True
            
    master = thismaster()
    piezo = Piezo(master)
    piezo.setup_piezo()
    piezo.stop_monitoring()
    
    
    time.sleep(0.2)
    piezo.goto(0,0,0)
    time.sleep(0.3)
        
    for i in range(15):
        print(f'====== {i} ======')
        coords = []
        for n in (0, 80):
            piezo.goto(n,n,n)
            time.sleep(1)
            x,y,z = piezo.measure_loc()
            coords.append((x,y,z))
        print(f'x: {coords[0][0]}, {coords[1][0]}')
        print(f'y: {coords[0][1]}, {coords[1][1]}')
        print(f'z: {coords[0][2]}, {coords[1][2]}')
    
    piezo.stop()
    
    zeros = [t for t in coords if t[0] < 50]
    maxes = [t for t in coords if t[0] >= 50]
    
    xz, yz, zz = zip(*zeros)
    xm, ym, zm = zip(*maxes)
    
    print(f'X: {np.mean(xz):0.3f} ± {np.std(xz):0.3f}, {np.mean(xm):0.3f} ± {np.std(xm):0.3f}')
    print(f'Y: {np.mean(yz):0.3f} ± {np.std(yz):0.3f}, {np.mean(ym):0.3f} ± {np.std(ym):0.3f}')
    print(f'Z: {np.mean(zz):0.3f} ± {np.std(zz):0.3f}, {np.mean(zm):0.3f} ± {np.std(zm):0.3f}')
        
    
    
    piezo.stop()
    
    
    
    
