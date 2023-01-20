import time
import os
import shutil


input_file  = r'C:/ProgramData/HEKA/com/E9Batch.In'
output_file = r'C:/ProgramData/HEKA/com/E9Batch.Out'

DEFAULT_SAVE_PATH = r'D:\Brian\SECM'

gl_st = time.time()
     

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
                if (lines != self.last and lines != None):
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
        
        self.file = input_file   # For EPC10 batch communication
        self.num = 0
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n')
        self.send_command('Echo startup')
        
        self.pgf_params = {}
        
    
        
    def running(self):
        self.status = 'running'
    
    
    def idle(self):
        self.status = 'idle'
     
        
    def isRunning(self):
        return self.status == 'running'
    
    
    def test_btn(self):
        self.save_last_experiment()
        return
     
        
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
    
    
    def abort(self):
        # Send commands to halt measurement
        self.idle() # Overwrite self.status
        self.macro('N Break 1')
        time.sleep(0.2)
        self.macro('N Stop 1')
        self.idle()
        self.macro('N Break 1')
        time.sleep(0.2)
        self.macro('N Stop 1')
        time.sleep(0.1)
        self.macro('N Store 1')
                   
    
    def save_last_experiment(self, path=None, name=''):
        # There is a bug in PATCHMASTER which does not allow the
        # "Export" macro to accept a user-defined path. So, we
        # save to the default path (which is the same as the 
        # current DataFile path) and copy the file to the desired location
        self.send_command('GetParameters DataFile')
        # while True:
        response = self.master.HekaReader.last[1]
            # if response[1].startswith('Reply'): break
        
        savepath = response.lstrip('Reply_GetParameters ').strip('"')
        savepath = savepath.replace('.dat', '.asc')
        if os.path.exists(savepath):
            os.remove(savepath)
        self.send_command('Export overwrite, test.asc')
        
        while True: # Wait for file creation by PATCHMASTER
            response = self.master.HekaReader.last
            try:
                if response[1].startswith('error'):
                    print('file export error!')
                    return
                if response[1].startswith('Reply_Export'):
                    break
            except: pass # Response may be None or a single '+000xx'
        
        # Copy file to new path
        if path:
            path = os.path.join(path, f'{name}.asc')
            
        else: 
            
            self.send_command('GetParameters SeriesDate, SeriesTime')
            SeriesDate, SeriesTime = self.master.HekaReader.last[1].split(',')

            SeriesDate = SeriesDate.lstrip('Reply_GetParameters ').replace('/', '')
            SeriesTime = SeriesTime[:-4].replace(':', '-')

            folder_path = os.path.join(DEFAULT_SAVE_PATH, SeriesDate)
            os.makedirs(folder_path, exist_ok=True)
            copy_path = os.path.join(folder_path, SeriesTime +f'-{name}.asc')
            path = copy_path
        
        shutil.copy2(savepath, path)
        print(f'Saved to {path}')
        return
    
     
        
     
    #### EXPERIMENT DEFINITIONS ####
        
    def update_Values(self, values):
        # PATCHMASTER maps Value i to p{i+1}... but calls it Value-{i+1} in GUI

        old_params = self.pgf_params
        vals_to_update = {}
        for key, val in values.items():
            old_val = old_params.get(key, None)
            if val != old_val:
                vals_to_update[key] = val
        
        for i, val in vals_to_update.items():
            self.send_command(f'SetValue {int(i)} {val}')
        self.send_command('ExecuteProtocol _update_pgf_params_')
        self.pgf_params = values
      
        
    def setup_CV(self, E0, E1, E2, E3, scan_rate, quiet_time):
        '''
        Apply amplifier/ filter settings
        
        Update CV parameters
        '''
        if self.isRunning(): return
        if scan_rate <= 0: raise ValueError('Scan rate must be > 0')
        values, duration = generate_CV_params(E0, E1, E2, E3, 
                                              scan_rate, quiet_time)
        
                
        # Get and set amplifier params from GUI module        
        self.running()
        
        # Set CV parameters
        self.update_Values(values)
        self.send_command('SelectSequence _reset')
        self.send_command('SelectSequence _CV')
        
        self.CV_params   = values
        self.CV_duration = duration
        self.idle()
    
    
    def run_CV(self, mode='normal'):
        # TODO: implement high sampling rate CV
        cmds = {
                'normal': '_CV',        # 10 Hz sampling  
                'fast':   '_CV-fast',   # 1 kHz sampling
                'hispeed':'_CV-hispeed' # 10 kHz sampling
                }
        self.send_command('ExecuteSequence _CV')
    
        
    def run_CV_loop(self, save_path=None, name=''):
        if self.isRunning():
            print('already running')
            return
        self.running()
        self.run_CV()
        st = time.time()
        while time.time() - st < self.CV_duration + 3:
            self.send_command('Query')
            try:
                if self.master.HekaReader.last[1] == 'Query_Idle':
                    break
            except:
                pass
            time.sleep(0.5)
        if not self.master.HekaReader.last[1] == 'Query_Idle':
            print('CV failed!')
            return
        self.save_last_experiment(path=save_path, name=name)
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


    