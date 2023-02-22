import serial
import time
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
        self._is_polling  = False
        self._STOP_POLLING = False
        
        if not self.master.TEST_MODE:
            self.port = serial.Serial(port = SER_PORT, timeout=0.5)
            self.setup(n_channels=2)
            
        self.pollingcount = 0
        self.pollingdata  = [[0],]
    
    
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
    def setup(self, n_channels=2, srate=1000, dec=1, deca=1, ps=6):
        # TODO: input checks
        self.number_of_channels = n_channels
        self.ps = ps         # packet size = 2**(ps + 4) bytes, min = 2**(0 + 4) = 32
        self.port.write(b"stop\r")        #stop in case device was left scanning
        self.port.write(b"encode 0\r")    #set up the device for binary mode
        self.port.write(b"slist 0 0\r")   #scan list position 0 channel 0
        if n_channels == 2:
            self.port.write(b"slist 1 1\r")
        self.port.write(f"srate {srate}\r".encode('utf-8')) #write scanning params
        self.port.write(f"dec {dec}\r".encode('utf-8'))
        self.port.write(f"deca {deca}\r".encode('utf-8'))
        self.port.write(f"ps {ps}\r".encode('utf-8')) # packet size
        time.sleep(0.5)
        while True:
            i = self.port.in_waiting
            if i > 0:
                response = self.port.read(i)
                break
        self.log('ADC setup complete')
        return
    
    
    
    def polling(self, timeout=2):
        '''
        Polling mode recording.
        
        ADC samples continuously until timeout. While sampling, 
        the most recent 100 points [index, time, V, I] are stored 
        in self.pollingdata. 
        
        This function should be run in its own thread. self.isPolling()
        is the check to make sure the ADC is not already polling data
        in another thread. To stop polling, another module should 
        call ADC.STOP_POLLING(). Alternatively, polling halts on 
        master.ABORT. 
        '''
        if self.isPolling(): return
        numofbyteperscan = 2**(self.ps + 4)
        idxs = []
        data = [ [] for _ in range(self.number_of_channels)]
        t    = []
        
        self.pollingdata = [idxs, t, *data]
        self.pollingcount += 1
        self.port.reset_input_buffer()
        self.port.write(b"start\r")
        self.polling_on()
        self.log('Starting polling', quiet=True)
        
        st = time.time()
        idx = 0
        
        while True:
            if time.time() - st > timeout:
                # print('ADC timeout')
                break
            if self._STOP_POLLING:
                self._STOP_POLLING = False
                break
            if self.master.ABORT:
                break
            i = self.port.in_waiting
            if (i//numofbyteperscan) > 0:
                response = self.port.read(i - i%numofbyteperscan)
                for x in range(0, self.number_of_channels):
                    adc=response[x*2]+response[x*2+1]*256
                    if adc>32767:
                        adc=adc-65536
                    adc *= (10/2**15) # +- 10 V full scale, 16 bit
                    data[x].append(adc)
                
                idxs.append(idx)
                t.append(time.time() - st)
                idx += 1
                if len(t) > 100:
                    # Only save most recent 100 pts
                    t = t[-100:] 
                    idxs = idxs[-100:]
                    data = [
                        l[-100:] for l in data
                        ]
                self.pollingdata = [idxs, t, *data]
        
        # TODO: aborting in between scans (sometimes?) causes an error here
        freq = self.pollingdata[0][-1]/(self.pollingdata[1][-1])
        
        # print(f'Sampling frequency: {freq:0.2f} Hz')
        
        self.port.write(b"stop\r")
        self.polling_off()
        self.log('Ending polling', quiet=True)
        
        return idxs, t, data
      
