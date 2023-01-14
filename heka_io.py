import time
import os
import threading


input_file  = r'C:/ProgramData/HEKA/com/E9Batch.In'
output_file = r'C:/ProgramData/HEKA/com/E9Batch.Out'

gl_st = time.time()

class master:
    
    def __init__(self):
        self.willStop = False
        self.STOP = False
        self.modules = [self]
        
    def register(self, module):
        # register a submodule to master
        setattr(self, module.__class__.__name__, module)
        self.modules.append(getattr(self, module.__class__.__name__))
    
    def run(self):
        while True:
            if time.time() - gl_st > 60: 
                break
            
            for module in self.modules:
                if module.willStop:
                    self.STOP = True
                    print('master stopped')
                    return
            time.sleep(0.5)

        

        ######################################
        #####                            #####
        #####     HEKA READER CLASS      #####                            
        #####                            #####
        ######################################
        
class HekaReader:
    # Class for reading PATCHMASTER's responses in /E9Batch.Out
    def __init__(self, master, output_file=output_file):
        self.master = master
        self.master.register(self)
        self.file = output_file
        self.last = None
        self.willStop = False
        if os.path.exists(self.file):
            with open(self.file, 'w') as f: 
                f.close()
    
    
    def test_read(self, timeout=60):
        st = time.time()
        while True:
            if time.time() - st > timeout:
                print('reader timeout')
                break
            if self.master.STOP:
                print('reader got stop command')
                break
            if time.time() - st > timeout:
                print('reader timeout')
                break
        self.willStop = True
    
    
    def read_stream(self, timeout=60):
        st = time.time()
        while True:
            if self.master.STOP:
                print('reader got stop command')
                self.willStop = True
                break
            
            with open(self.file, 'r') as f:
                lines = [line.rstrip() for line in f]
                if lines != self.last:
                    # print(f'Response: {lines} {time.time() - gl_st:0.4f}')
                    self.last = lines







        ######################################
        #####                            #####
        #####     HEKA WRITER CLASS      #####                            
        #####                            #####
        ######################################

class HekaWriter:
    # Class to control writing commands to PATCHMASTER
    # TODO: sometimes double sends commands
    def __init__(self, master, input_file=input_file):
        self.master = master
        self.master.register(self)
        self.willStop = False
        self.status = 'idle'
        
        self.file = input_file
        self.num = 0
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n')
        
        self.send_command('Echo startup')
    
        
    def running(self):
        self.status = 'running'
    
    def idle(self):
        self.status = 'idle'
        
    def isRunning(self):
        return self.status == 'running'
    
    def test_write(self, timeout=3):
        st = time.time()
        while True:
            print('writer')
            if self.master.STOP:
                print('writer got stop command')
                self.willStop = True
                break
            if time.time() - st > timeout:
                print('writer timeout')
                self.willStop = True
                break
            time.sleep(1)
        
    def send_command(self, cmd):
        # print(f'Sending: {self.num} {cmd}')
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n{cmd}')
        self.num += 1
        time.sleep(0.2)
    
    
    def macro(self, cmd):
        if not self.isRunning():
            self.running()
            self.send_command(f'Set {cmd}')
            self.idle()
            
    
    def save_last_experiment(self):
        # Select last <Series>
        # Run export protocol
        # TODO: set export path somehow
        self.send_command('Export overwrite "C:/Users/BRoehrich/Desktop/test_export.asc"')
        return
     
        
     
    #### EXPERIMENT DEFINITIONS ####
        
    def update_Values(self, values):
        # PATCHMASTER maps Value i to p{i+1}... but calls it Value-{i+1} in GUI
        for i, val in values.items():
            self.send_command(f'SetValue {int(i)} {val}')
        self.send_command('ExecuteProtocol _update_pgf_params_')
      
        
    def setup_CV(self, E0, E1, E2, E3, scan_rate, quiet_time):
        '''
        Apply amplifier/ filter settings
        
        Update CV parameters
        '''
        if self.isRunning(): return
        if scan_rate <= 0: raise ValueError('Scan rate must be > 0')
        values, duration = generate_CV_params(E0, E1, E2, E3, 
                                              scan_rate, quiet_time)
        
        
        print('CV setup')
        
        # Get and set amplifier params from GUI module
        self.master.GUI.set_amplifier()
        
        self.running()
        
        # Set CV parameters
        self.update_Values(values)
        self.send_command('SelectSequence _reset')
        self.send_command('SelectSequence _CV')
        
        self.CV_params = values
        self.CV_duration = duration
        self.idle()
    
    
    def run_CV(self):
        self.send_command('ExecuteSequence _CV')
        
    def run_CV_loop(self):
        if self.isRunning():
            print('already running')
            return
        self.running()
        self.run_CV()
        st = time.time()
        while time.time() - st < self.CV_duration + 3:
            self.send_command('Query')
            if self.master.HekaReader.last[1] == 'Query_Idle':break
            time.sleep(0.5)
        self.idle()
        if __name__ == '__main__':
            self.willStop = True
        
      
        
      
        

def generate_CV_params(E0, E1, E2, E3, scan_rate, quiet_time):
    '''
    *** POTENTIALS IN V, SCAN_RATE IN V/s, QUIET_TIME IN s ***
    1. Hold at E0 for quiet_time
    2. Ramp to E1 at scan_rate
    3. Ramp to E2 at scan_rate
    4. Ramp to E3 (end potential) at scan_rate
    
    Parameter assignments:
            0: Holding potential (V)
            1: Holding time      (s)
            2: E1 potential      (V)
            3: E1 ramp time      (s)
            4: E2 potential      (V)
            5: E2 ramp time      (s)
            6: End potential     (V)
            7: End ramp time     (s)
    '''
    rt1 = abs(E1 - E0) / scan_rate
    rt2 = abs(E2 - E1) / scan_rate
    rt3 = abs(E3 - E2) / scan_rate
    
    duration = quiet_time + rt1 + rt2 + rt3
    
    values = {
        0: E0,
        1: quiet_time,
        2: E1,
        3: rt1,
        4: E2,
        5: rt2,
        6: E3,
        7: rt3
        }
    return values, duration
    


if __name__ == '__main__':
    master = master()
            
    writer = HekaWriter(master, input_file)
    reader = HekaReader(master, output_file)
    
    
    # timeout = 5
    # master_thread = threading.Thread(target=master.run)
    # writer_thread = threading.Thread(target=writer.run_CV_loop)
    # reader_thread = threading.Thread(target=reader.read_stream)
    
    # master_thread.start()
    # writer_thread.start()
    # reader_thread.start()
    
    # master_thread.join()
    # writer_thread.join()
    # reader_thread.join()


    