import serial
import time
import struct
import numpy as np
from modules.DataStorage import ADCDataPoint
from utils.utils import run, Logger

CONST_SER_PORT = 'COM6'   #get the com port from device manger and enter it here


class ADC(Logger):
    '''
    https://github.com/dataq-instruments/Simple-Python-Examples/blob/master/simpletest_binary.py
    
    Controller for DATAQ DI-2108. ONLY used to monitor voltage and 
    current in real time during experiments. Saved data is instead 
    read from HEKA save files.     
    '''
    
    
    def __init__(self, master=None, SER_PORT = CONST_SER_PORT):
        if master:
            self.master = master
            self.master.register(self)
        self.willStop   = False
        self._is_setup  = False
        self._is_polling  = False
        self._STOP_POLLING = False
        
        # Default ADC parameters, refer to DI-2108 manual for definitions
        self.params = {
            'n_channels': 2,
            'srate'     : 800,
            'dec'       : 1,
            'deca'      : 1,
            'ps'        : 1, # packet size = 2**(ps + 4) bytes, min = 2**(1 + 4) = 32
                             # !!! Min ps = 1 or else buffer overflows !!!
            }
        
        
        if not self.master.TEST_MODE:
            self.port = serial.Serial(port = SER_PORT, timeout=0.5)
            self.setup()
            
        self.pollingcount = 0
        self.pollingdata  = ADCDataPoint(loc=(0,),
                                         data=[ [], [], [] ])
        self.set_sample_rate(100)
    
    
    # Command
    def STOP_POLLING(self): 
        self._STOP_POLLING = True
    
    
    # Set flags
    def polling_on(self): 
        self._is_polling   = True
        self._STOP_POLLING = False
        
    
    # Set flag   
    def polling_off(self): 
        self._is_polling = False
    
    
    # Check flag
    def isPolling(self): 
        return self._is_polling
    
    
    # Stop recording and close serial port
    def stop(self):
        try:
            self.port.write(b"stop\r")
        except: # port is already closed
            return
        time.sleep(1)
        self.port.close()
        self.log('Serial port closed')
        return
       
    # Set up serial port
    def setup(self, params=None):
        
        if self.master.TEST_MODE:
            return
        
        if not params:
            params = {}
        
        new_params = {
            'n_channels': params.get('n_channels', self.params['n_channels']),
            'srate'     : params.get('srate', self.params['srate']),
            'dec'       : params.get('dec', self.params['dec']),
            'deca'      : params.get('deca', self.params['deca']),
            'ps'        : params.get('ps', self.params['ps']),
            }
        
        if (new_params == self.params) and self._is_setup:
            return
        
        self.params = new_params
                
        
        self.port.write(b"stop\r")        #stop in case device was left scanning
        self.port.write(b"encode 0\r")    #set up the device for binary mode
        self.port.write(b"slist 0 0\r")   #scan list position 0 channel 0
        if self.params['n_channels'] == 2:
            self.port.write(b"slist 1 1\r")
        
        #write scanning params
        self.port.write(f"srate {self.params['srate']}\r".encode('utf-8')) 
        self.port.write(f"dec {self.params['dec']}\r".encode('utf-8'))
        self.port.write(f"deca {self.params['deca']}\r".encode('utf-8'))
        self.port.write(f"ps {self.params['ps']}\r".encode('utf-8')) # packet size
        time.sleep(0.5)
        while True:
            i = self.port.in_waiting
            if i > 0:
                response = self.port.read(i)
                # print(response)
                break
        self.log('ADC setup complete', quiet=True)
        self._is_setup = True
        return
    
    
    def set_sample_rate(self, freq):
        # Adjust sampling parameters to match desired sample rate
        # with maximal filtering
        
        srate = 400*self.params['n_channels'] # minimum srate = fastest base freq
        
        # Maximum sample rate is ~70 kHz for 2 channels
        
        dec = 70000//freq
        deca = 1
        while dec > 512:
            dec //= 10
            deca *= 10
            
        self.setup(params={'srate': srate,
                           'dec'  : dec,
                           'deca' : deca})                
        return
    
    
    def polling(self, timeout=3, params=None):
        '''
        Polling mode recording.
        
        ADC samples continuously until timeout. While sampling, 
        data are stored in self.pollingdata as an ADCDataPoint object. 
        
        This function should be run in its own thread. self.isPolling()
        is the check to make sure the ADC is not already polling data
        in another thread. To stop polling, another module should 
        call ADC.STOP_POLLING(). Alternatively, polling halts on 
        master.ABORT. 
        
        ARGUMENTS:
            timeout: int, polling mode timeout
            params: dict, passed to self.setup()
        
        RETURNS:
            None
        '''
        if self.isPolling(): return
        
        # Initialize
        self.setup(params)
        numofbyteperscan = 2*self.params['n_channels']
        idxs = []
        data = [ [] for _ in range(self.params['n_channels'])]
        t    = []
        
        
        # Setup data saving structure
        self.pollingdata = ADCDataPoint(loc=(0,),
                                        data=[t,
                                              [],
                                              [],]
                                        )
        
        gain = 1e9 * self.master.GUI.amp_params.get('float_gain', 1e-9)
        self.pollingdata.set_HEKA_gain(gain)
        self.master.Plotter.FIG2_FORCED = False
        
        # Start reading ADC
        self.pollingcount += 1
        self.port.reset_input_buffer()
        self.port.write(b"start\r")
        self.polling_on()
        self.log('Starting polling', quiet=False)
        
        
        idx = 0
        st = time.perf_counter_ns() # Need maximum precision here
        last_timepoint = 0
        while True:
            # Stop conditions
            if time.perf_counter_ns() - st > timeout*1e9:
                self.log('Timed out', quiet=True)
                break
            if self._STOP_POLLING:
                self._STOP_POLLING = False
                break
            if self.master.ABORT:
                break
            
            # Check for new data block
            i = self.port.in_waiting
            
            if (i//numofbyteperscan) > 0:
                '''
                https://github.com/dataq-instruments/Simple-Python-Examples/blob/master/simpletest_binary2.py
                '''
                
                data = [ [] for _ in range(self.params['n_channels'])]
                
                response = self.port.read(i - i%numofbyteperscan)
                count = (i - i%numofbyteperscan)//2
                
                bResponse = bytearray(response)
                Channel = struct.unpack("<"+"h"*count, bResponse)
                
                for j in range(count):
                    ch = (count - j)%2
                    data[ch].append(Channel[j]*10/2**15)
                
                
                
                # calculate what time each point was measured
                # Assumes all channels measured simultaneously (they're not)
                this_timepoint = time.perf_counter_ns() - st
                dt = (this_timepoint - last_timepoint) / len(data[0])
                
                ts = list(1e-9*np.arange(last_timepoint,
                                         this_timepoint,
                                         dt)
                          )
                
                # Save this block of data
                self.pollingdata.append_data(ts,
                                             data[0],
                                             data[1])
                self.pollingdata.reset_times() # make time points evenly spaced
                
                # Reset time counter
                last_timepoint = this_timepoint
                idxs.append(idx)
                idx += 1
        
        # TODO: aborting in between scans (sometimes?) causes an error here
        try:
            times = self.pollingdata.data[0]
            freq = times[-1]/len(times)
            freq = 1/freq
            # print(f'Sampling frequency: {freq:0.2f} Hz')
        except Exception as e:
            print(f'Error calculating frequency: {e}')
        
        self.port.write(b"stop\r")
        time.sleep(0.1)
        i = self.port.in_waiting
        if i > 0: # clear port
            self.port.read(i)
        self.polling_off()
        self.log('Ending polling', quiet=True)
        
        return
    
    
    def record(self):
        self.port.write(b'start\r')
        st = time.time()
        while time.time() - st < 2:
            i = self.port.in_waiting
            if i > 0:
                response = self.port.read(i)
                print(response)
        self.port.write(b"stop\r")
        self.stop()
        


if __name__ == '__main__':
    class thisMaster():
        # minimal class to pass to ADC for ADC testing purposes
        def __init__(self):
            self.TEST_MODE = False
            self.ABORT = False
            self.GUI = self.Plotter = self
            self.amp_params = {}
            self.FIG2_FORCED = False
            self.register = lambda x:0
            
    master = thisMaster()
    adc = ADC(master=master)
    # adc.polling()
    for freq in [10000, 2000, 1000, 100]:
        print('')
        print(f'requested freq {freq}')
        adc.set_sample_rate(freq)
        adc.polling()
        data = adc.pollingdata.get_data()
        print(f'{len(data[0])} pts, max {max(data[0])} s')
    adc.stop()
    
        
