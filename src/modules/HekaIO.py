import time
import os
import psutil
import shutil
import json
from ..utils.utils import run, Logger
from ..utils.EIS_util import generate_tpl
from functools import partial


input_file  = r'C:/ProgramData/HEKA/com/E9Batch.In'
output_file = r'C:/ProgramData/HEKA/com/E9Batch.Out'

DEFAULT_SAVE_PATH = r'D:/SECM/Data'

gl_st = time.time()
     



        ######################################
        #####                            #####
        #####     HEKA READER CLASS      #####                            
        #####                            #####
        ######################################
        
class HekaReader(Logger):
    '''
    Class for reading PATCHMASTER's responses in /E9Batch.Out
    
    The last response is stored in HekaReader.last and should be checked
    immediately after a command is sent, because it could get overwritten
    by a subsequent message
    '''
    def __init__(self, master, output_file=output_file):
        self.master = master
        self.master.register(self)
        self.file = output_file
        self.last = None
        self.willStop = False
        if os.path.exists(self.file):
            with open(self.file, 'w') as f: 
                f.close()
    
    def PatchmasterRunning(self):
        # Checks if PATCHMASTER is currently running
        for p in psutil.process_iter():
            if 'PatchMaster.exe' in p.name():
                return True
        return False
        
    
    def test_read(self, timeout=60):
        # Test function
        st = time.time()
        while True:
            if time.time() - st > timeout:
                break
            if self.master.STOP:
                break
        self.willStop = True
    
    
    def read_stream(self):
        '''
        Call in its own thread. Reads HEKA output file continuously
        until receives stop command from master. Stores the last
        output in self.last.
        '''
        while True:
            if self.master.STOP:
                self.willStop = True
                break
            
            if not os.path.exists(self.file): continue
            
            with open(self.file, 'r') as f:
                lines = [line.rstrip() for line in f]
                if (lines != self.last and lines != None):
                    # print(f'Response: {lines} {time.time() - gl_st:0.4f}')
                    self.last = lines
        self.log('Stopped reading')







        ######################################
        #####                            #####
        #####     HEKA WRITER CLASS      #####                            
        #####                            #####
        ######################################

class HekaWriter(Logger):
    '''
    Class to control writing commands to PATCHMASTER
    
    Commands are written to the file E9Batch.In as documented in the 
    PATCHMASTER tutorial (included in this repo, /docs/pm_tutorial.pdf)
    
    From testing, it seems that PATCHMASTER can only read commands every
    ~50-100 ms. So, each command is followed by a 100ms delay to assure 
    all commands are read.
    
    We can write a series of commands to the file simultaneously and 
    PATCHMASTER will execute them all in order. This is useful for setting
    amplifier and CV parameters, for example, bypassing the 200ms delay between
    each command. 
    
    '''
    def __init__(self, master, input_file=input_file):
        self.master = master
        self.master.register(self)
        self.willStop = False
        self.status = 'idle'
        if self.master.TEST_MODE:
            return
        
        self.file = input_file   # For EPC10 batch communication
        self.num = 0
        
        self.clear_file()
        self.send_command('Echo startup')
        self.send_command('SetSleep 0.01')
        
        self.pgf_params = {}
        self.CV_params  = None
        self.EIS_params = None
        self.EIS_WF_params = None
        self.EIS_corrections = None
        
    
        
    def running(self):
        self.status = 'running'
    
    
    def idle(self):
        self.status = 'idle'
     
        
    def isRunning(self):
        return self.status == 'running'
         
        
    def send_command(self, cmd):
        # print(f'Sending: {self.num} {cmd}')
        if self.master.TEST_MODE:
            return
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n{cmd}\n')
        self.num += 1
        time.sleep(0.1)
       
        
    def send_multiple_cmds(self, cmds):
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n')
            for cmd in cmds:
                f.write(f'{cmd}\n')
        self.num += 1
        time.sleep(0.1)
    
    
    def clear_file(self):
        with open(self.file, 'w') as f:
            f.close()
        self.num = 0
    
    
    def macro(self, cmd):
        '''
        Send a macro command as given in docs/HEKA Macro Commands.txt
        '''
        if not self.isRunning():
            self.running()
            self.send_command(f'Set {cmd}')
            self.idle()
    
    
    
    def abort(self):
        # Send commands to halt measurement
        self.idle() # Overwrite self.status
        self.macro('N Break 1')
        self.macro('N Stop 1')
        self.idle()
        self.macro('N Break 1')
        self.macro('N Stop 1')
        self.macro('N Store 1')
        self.idle()
    
    
    def isDataFile(self):
        '''
        Query PATCHMASTER to check whether a DataFile is 
        currently open to save to
        '''
        self.send_command('GetParameters DataFile')
        st = time.time()
        while time.time() - st < 1:
            try:
                response = self.master.HekaReader.last[1]
                if response.split(' ')[-1] == '""':
                    return False
                return True
            except:
                continue
        self.log('Timed out waiting for PATCHMASTER to respond with current data file')
        return False
    

    def set_ascii_export(self):
        self.send_command('Set @  ExportTarget  "ASCII"')
        
        
    def set_matlab_export(self):
        self.send_command('Set @  ExportTarget  "MatLab"')
               
    
    def save_last_experiment(self, path=None):
        '''
        There is a bug in PATCHMASTER which does not allow the
        "Export" macro to accept a user-defined path. So, we
        save to the default path (which is the same as the 
        current DataFile path) and copy the file to the desired path
        '''
        self.send_command('GetParameters DataFile')
        st = time.time()
        while time.time() - st < 1:
            response = self.master.HekaReader.last[1]
            if response[1].startswith('Reply_GetParameters'): 
                break
        
        savepath = response.lstrip('Reply_GetParameters ').strip('"')
        savepath = savepath.replace('.dat', '')
        savepath += '.asc'
        if os.path.exists(savepath):
            os.remove(savepath)
        
        # Select Series level for full export
        self.send_command('GetTarget')
        while True:
            if self.master.HekaReader.last[1].startswith('Reply_GetTarget'):
                dat = self.master.HekaReader.last[1].split('  ')[1]
                group, ser, sweep, trace, target = dat.split(',')
                self.send_command(f'SetTarget {group},{ser},{sweep},{trace},2,TRUE,TRUE')
                break
            
        # Set oscilloscope to show full time, 0-> 100%. Otherwise,
        # PATCHMASTER only exports the times displayed on the scope
        time.sleep(0.1)
        self.send_multiple_cmds([f'Set O Xmin 0',
                                 f'Set O Xmax 100',
                                 f'Set O AutoSweep'])
        
        # Hopping mode --> export as .mat
        # Otherwise, as ascii
        if (not path or path == 'None/.asc'):
            self.set_ascii_export()
        else:
            self.set_matlab_export()
            savepath = savepath.replace('.asc', '.mat')
            path     = path.replace('.asc', '.mat')
        
        
        self.send_command(f'Export overwrite, {savepath}')
        
        st = time.time()
        while True: # Wait for file creation by PATCHMASTER
            response = self.master.HekaReader.last
            if time.time() - st > 30:
                self.log('save_last_experiment timed out waiting for PATCHMASTER!')
                return ''
            try:
                # if response[1].startswith('error'):
                #     self.log('File export error!')
                #     print('file export error!')
                #     return ''
                if response[1].startswith('Reply_Export'):
                    break
            except: pass # Response may be None or a single '+000xx'
        
        
        if (not path or path == 'None/.asc'): 
            # Data was not recorded as part of a scanning experiment
            # Save it with the timestamp
            self.send_command('GetParameters SeriesDate, SeriesTime')
            time.sleep(0.01)
            SeriesDate, SeriesTime = self.master.HekaReader.last[1].split(',')

            SeriesDate = SeriesDate.lstrip('Reply_GetParameters ').replace('/', '')
            SeriesTime = SeriesTime[:-4].replace(':', '-')

            folder_path = os.path.join(DEFAULT_SAVE_PATH, SeriesDate)
            os.makedirs(folder_path, exist_ok=True)
            path = os.path.join(folder_path, f'{SeriesTime}.asc')
        
        
        base_path = os.path.split(path)[0]
        os.makedirs(base_path, exist_ok=True)
        
        try:
            shutil.copy2(savepath, path)
            self.log(f'Saved to {path}', 1)
        except Exception as e:
            self.log(f'savepath: {savepath}')
            self.log(f'path: {path}')
            self.log(f'Saving error: {e}')
        return path
    
     
        
     
    #### EXPERIMENT DEFINITIONS ####
    
    def reset_amplifier(self):
        '''
        Sends commands to set amplifier back to default (CV) state
        '''
        cmds = ['Set E StimFilter 1',
                'Set E TestDacToStim1 0',
                'Set E Mode 3',
                'Set E Filter1 2',
                'Set E F2Response 0',
                'Set E Filter2 0.5']
        self.send_multiple_cmds(cmds)
        
        
        
    def update_Values(self, values):
        # Update Values which are used to define CV, CA, etc voltages, timings, ...
        # PATCHMASTER maps Value i to p{i+1}... but calls it Value-{i+1} in GUI

        old_params = self.pgf_params
        vals_to_update = {}
        for key, val in values.items():
            old_val = old_params.get(key, None)
            if val != old_val:
                vals_to_update[key] = val
        
        cmds = []
        for i, val in vals_to_update.items():
            cmds.append(f'SetValue {int(i)} {val}')
        cmds.append('ExecuteProtocol _update_pgf_params_') # Set PgfParams = Values
        self.send_multiple_cmds(cmds)
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
        
        self.CV_params   = values
        self.CV_duration = duration
        self.idle()
        self.log('Set CV parameters')
    
    
    def run_CV(self, mode='normal'):
        cmds = {
                '10Hz'  : '_CV-10Hz', 
                '100Hz' : '_CV-100Hz',
                '1kHz'  : '_CV-1kHz',
                '10kHz' : '_CV-10kHz',
                }
        
        # Determine which sampling rate to use
        E1 = self.CV_params[0] 
        E0 = self.CV_params[2]
        ti = self.CV_params[3]
        scan_rate = abs(E1 - E0) / ti
        if scan_rate <= 0.1:
            mode = '10Hz'
        elif scan_rate > 0.1 and scan_rate <= 0.5:
            mode = '100Hz'
        elif scan_rate > 0.5:
            mode = '1kHz'
        
        cmd = cmds[mode]
        self.log(f'CV {cmd}', quiet=True)
        self.send_command(f'ExecuteSequence {cmd}')
        self.running()
      

    def setup_EIS(self, E0, f0, f1, n_pts, n_cycles, amp):
        '''
        Set amplifier to hold DC bias
        Set filters
        Update EIS parameters in PATCHMASTER
        '''
        if self.isRunning(): return
        values, duration = generate_EIS_params(E0/1000, n_cycles*min(f0, f1))
        
        self.running()
        
        cmds = get_filters(max(f0, f1))         # Set filters based on max frequency
        cmds.append('Set E StimFilter 0')       # Set stim filter to 2 us
        cmds.append('Set E TestDacToStim1 2')   # Turn on external input for Stim-1
        cmds.append('Set E ExtScale 1')         # Set external scale to 1
        cmds.append('Set E Mode 3')
        self.send_multiple_cmds(cmds)
        
        self.send_command(f'Set E Vhold {E0}')  # Set DC bias
        time.sleep(1)
        
        # Update pgf fields
        self.update_Values(values)
        self.EIS_params   = values
        self.EIS_duration = duration
        
        EIS_WF_params = {'E0':E0, 'f0':f0, 'f1':f1, 'n_pts':n_pts, 
                         'n_cycles': n_cycles, 'amp':amp}
        
        if EIS_WF_params != self.EIS_WF_params:
            self.EIS_applied_freqs = self.make_EIS_waveform(E0, f0, f1, n_pts, n_cycles, amp)
            self.check_EIS_corrections(EIS_WF_params)
        
        self.EIS_WF_params = EIS_WF_params
        self.idle()
        self.log('Set EIS parameters')
        return
    
    
    def make_EIS_waveform(self, E0, f0, f1, n_pts, n_cycles, amp):
        applied_freqs = generate_tpl(f0, f1, n_pts, n_cycles, 
                                     amp, 'D:/SECM/_auto_eis_1.tpl')
        self.log('Wrote new EIS waveform')
        return applied_freqs
    
    
    def check_EIS_corrections(self, EIS_WF_params):
        '''
        Checks if the current waveform is in the stored corrections file.
        
        If it is, take its correction factors from the file.
        
        Otherwise, prompt user to plug in the model circuit to record
        a reference waveform
        
        Corrections file is a json which stores a dictionary. Dictionary keys
        are defined by the waveform parameters: amplitude, number of points,
        and all the applied frequencies.
        
        d = {
            (amp, n_pts, *applied_frequencies) = [(Z_corr, phase_corr) for
                                                  f in applied frequencies]            
            }
                
        '''
        amp   = EIS_WF_params['amp']
        n_pts = EIS_WF_params['n_pts']
        key   = (amp, n_pts, *self.EIS_applied_freqs)
        file = 'src/utils/EIS_waveforms.json'
        if os.path.exists(file):
            d = json.load(file)
            if key in d:
                self.EIS_corrections = d[key]
                return
        
        # Prompt for model circuit
        
        # Record a spectrum
        
        # Save corrections to file
            
    
    
    def run_EIS(self):
        '''
        Send command to run single EIS scan
        '''
        self.send_command('ExecuteSequence _auto_eis')
        self.running()
        return
    
    
    def run_custom(self):
        '''
        Run the custom, user-set PGF file
        '''
        self.send_command('ExecuteSequence _custom')
        self.running()
        return
    
    
    def run_measurement_loop(self, measurement_type, save_path=None, name=''):
        '''
        Runs measurement of the requested type. Starts ADC polling in another
        thread. Saves the data.
        
        measurement_type: 'CV', 'CA', 'EIS'. Defines what to run
        save_path: string, path to save to
        name: string, name to save as. save_path/{name}.asc
        '''
        if self.isRunning():
            self.log('Got new CV command, but already running!')
            return
            
        if not self.isDataFile():
            print('== Open a DataFile in PATCHMASTER before recording! ==')
            return
        
        if measurement_type == 'CV':
            run_func = self.run_CV
            duration = self.CV_duration
        elif measurement_type == 'CA':
            run_func = self.run_CA
            duration = self.CA_duration
        elif measurement_type == 'EIS':
            run_func = self.run_EIS
            duration = self.EIS_duration
        elif measurement_type == 'Custom':
            run_func = self.run_custom
            duration = 3600
        else:
            print('Internal error: invalid measurement_type')
            return

        
        run_func()
        st = time.time()
        
        # Start ADC polling
        run(partial(self.master.ADC.polling, 
                    timeout = duration))
        
        # Measurement loop
        success = False
        while time.time() - st < duration + 3:
            if not self.isRunning():
                # Wait for run command to get sent to PATCHMASTER
                continue
            time.sleep(0.5)
            if self.master.ABORT:
                self.master.ADC.STOP_POLLING()
                self.abort()
                self.idle()
                return 'MEAS_ABORT'
            self.send_command('Query')
            try:
                if self.master.HekaReader.last[1] == 'Query_Idle':
                    success = True
                    break 
            except:
                pass
            
        if not success:
            self.log(f'Experiment {measurement_type} failed!')         
        
        self.master.ADC.STOP_POLLING()
        
        path = self.save_last_experiment(path=f'{save_path}/{name}.asc')
        self.idle()
        return path
    
      
        

def generate_CV_params(E0, E1, E2, E3, scan_rate, quiet_time):
    '''
    *** POTENTIALS IN V, SCAN_RATE IN V/s, QUIET_TIME IN s ***
    1. Hold at E0 for quiet_time
    2. Ramp to E1 at scan_rate
    3. Ramp to E2 at scan_rate
    4. Ramp to E3 (end potential) at scan_rate
    
    Parameter assignments:
            0: Holding potential (V) (p1)
            1: Holding time      (s) (p2)
            2: E1 potential      (V) (p3)
            3: E1 ramp time      (s) (p4)
            4: E2 potential      (V) (p5)
            5: E2 ramp time      (s) (p6)
            6: End potential     (V) (p7)
            7: End ramp time     (s) (p8)
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



def generate_EIS_params(E_DC, duration):
    '''
    *** POTENTIALS IN V, ***
    
    Parameter assignments:
        0: DC bias   (V) (p1)
        1: scan time (s) (p2)
    '''
    
    values = {
        0: E_DC,
        1: duration,
        }
    
    return values, duration


def get_filters(max_freq):
    '''
    Return appropriate setting for filter1 and filter2 based on the 
    
    maximum applied EIS freq
    '''
    
    filt1s = [10, 30, 100]
    best_filt1 = 100
    for filt in filt1s:
        if filt*1000 >= 3*max_freq:
            best_filt1 = filt
            break
    best_filt2 = 2*max_freq
    if best_filt2 > 8000:
        f2_val  = 8000
        f2_type = 2
    else:
        f2_val  = best_filt2
        f2_type = 0 # Sets as Bessel filter
        
    filter1options = [100, 30, 10]    # Order filters appear in PATCHMASTER
    f1_idx = [i for i, val in enumerate(filter1options) 
              if val == best_filt1][0]
    
    
    return [f'Set E Filter1 {f1_idx}', 
            f'Set E F2Response {f2_type}', 
            f'Set E Filter2 {f2_val/1000}']



    