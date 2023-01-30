import serial
import time
import numpy as np
import matplotlib.pyplot as plt
import threading

CONST_SER_PORT = 'COM6'   #get the com port from device manger and enter it here


srate = 1000
dec   = 1
deca  = 1

sara = 60_000_000/(srate * dec * deca)

def run(func, args=()):
    t = threading.Thread(target=func, args=args)
    t.start()
    return t

class ADC():
    '''
    https://github.com/dataq-instruments/Simple-Python-Examples/blob/master/simpletest_binary.py
    '''
    
    # TODO: add buffer of previous x seconds of currents data
    
    def __init__(self, master=None, SER_PORT = CONST_SER_PORT):
        if master:
            self.master = master
            self.master.register(self)
        self.willStop = False
        # self.port = serial.Serial(port = SER_PORT, timeout=0.5)
        self.pollingdata = [[0],]
    
    def stop(self):
        try:
            self.port.write(b"stop\r")
        except: # port is already closed
            return
        time.sleep(1)
        self.port.close()
        return
        
    def setup(self, n_channels=1, srate=1000, dec=1, deca=1, ps=6):
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
        return
    
    
    def polling(self, timeout=2):
        self.setup(n_channels=2)
        numofbyteperscan = 2**(self.ps + 4)
        idxs = []
        data = [ [] for _ in range(self.number_of_channels)]
        t    = []
        
        self.pollingdata = [0]
        self.port.reset_input_buffer()
        self.port.write(b"start\r")
        
        st = time.time()
        idx = 0
        self.master.Plotter.reinit_fig2()
        self.master.Plotter.poll_ADC()
        while True:
            if time.time() - st > timeout:
                print('stopping polling')
                break
            if self.master.ABORT:
                print('aborting polling')
                self.master.make_ready()
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
                        data[i][-100:] for i in range(len(data))
                        ]
                self.pollingdata = [idxs, t, *data]
        
        return idxs, t, data
    
    
    def plotter(self):
        fig, ax = plt.subplots()
        ln, = ax.plot([], [])
        ln2, = ax.plot([],[])
        fig.canvas.draw()
        bg = fig.canvas.copy_from_bbox(ax.bbox)
        ax.draw_artist(ln)
        ax.draw_artist(ln2)
        ax.set_xlim(-0.1, 2.1)
        ax.set_ylim(-0.7,0.7)
        fig.canvas.blit(ax.bbox)

        run(self.polling)
        st = time.time()
        plotted_idxs = [-1]
        plot_ts = []
        plot_ch1data = []
        plot_ch2data = []
        
        while time.time() - st < 3:
            last_idx = max(plotted_idxs)
            try:
                idxs, ts, ch1data, ch2data = self.pollingdata
            
                startpoint = min([i for i, val in enumerate(idxs)
                                  if val > last_idx])
            except:
                continue
            plotted_idxs += idxs[startpoint:]
            plot_ts += ts[startpoint:]
            plot_ch1data += ch1data[startpoint:]
            plot_ch2data += ch2data[startpoint:]
            ln.set_data(plot_ts, plot_ch1data)
            # ln.set_data(plot_ch1data, plot_ch2data)
            ln2.set_data(plot_ts, plot_ch2data)
            ax.draw_artist(ln)
            ax.draw_artist(ln2)
            fig.canvas.blit(ax.bbox)
            fig.canvas.draw_idle()
            plt.pause(0.1)
            
            
            
        
    
    
    
    def record(self, timeout=2):
        # Record for a set amount of time
        numofbyteperscan = 2**(self.ps + 4)
        
        self.port.reset_input_buffer()
        self.port.write(b"start\r")
        
        data = [ [] for _ in range(self.number_of_channels)]
        t    = []
        
        st = time.time()
        while True:
            if (self.master.ABORT or
                time.time() - st > timeout):   
                self.stop()
                print("ADC recording finished")
                if self.master.ABORT:
                    self.master.make_ready()
                break
            else:
                i= self.port.in_waiting
                if (i//numofbyteperscan)>0:
                    response = self.port.read(i - i%numofbyteperscan)
           
                    for x in range(0, self.number_of_channels):
                        adc=response[x*2]+response[x*2+1]*256
                        if adc>32767:
                            adc=adc-65536
                        adc *= (10/2**15) # +- 10 V full scale, 16 bit
                        data[x].append(adc)
                        
                    t.append(time.time() - st)
        
        times = np.linspace(t[0], t[-1], len(t))
        return times, data


    
        


if __name__ == '__main__':
    adc = ADC()
    adc.setup(n_channels=2)
    # adc.plotter()
    # idx, t, data = adc.polling()
    # t, data = adc.record()
    
    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots()
    # for i, d in enumerate(data):
    #     ax.plot(t, d, '.-', label=f'Channel {i}')
    # ax.set_ylabel('V')
    # ax.set_xlabel('t/ min')
    
    adc.stop()




