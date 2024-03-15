import time
import os
import psutil
import shutil
import json
import numpy as np
from tkinter import messagebox
from .FeedbackController import read_heka_data
from .DataStorage import EISDataPoint
from ..utils.utils import run, Logger, threads
from ..utils.EIS_util import generate_tpl, get_EIS_sample_rate
from functools import partial


# HEKA file paths
input_file  = r'C:/ProgramData/HEKA/com/E9Batch.In'
output_file = r'C:/ProgramData/HEKA/com/E9Batch.Out'

DEFAULT_SAVE_PATH = r'D:/SECM/Data'


class Potentiostat(Logger):
    ''' 
    Abstract base class defining all Potentiostat methods.
    All methods should be overwritten in potentiostat-specific subclasses
    '''
    
    status = 'idle'    
    
    def _error_msg(self, method_name):
        raise NotImplementedError(f'Method {method_name} not implemented in class {self.__class__}')
    
    
    def stop(self):
        '''
        Called by master when program stops.
        This function should close the potentiostat interface nicely.
        '''
        self._error_msg('stop')
        
        
    def isRunning(self):
        '''
        Returns: bool
        '''
        self._error_msg('isRunning')
        return
    
    
    def set_amplifier(self):
        '''
        Read amplifier settings from GUI
        Send commands to set amplifier
        
        Returns: bool, whether or not setup was successful
        '''
        self._error_msg('set_amplifier')
        return
    
    
    def setup_CV(self):
        '''
        Read CV settings from GUI
        Send commands to setup amplifier
        Store settings to self
        
        Returns: bool, whether or not setup was successful
        '''
        self._error_msg('setup_CV')
        return
    
    
    def setup_EIS(self):
        '''
        Read EIS settings from GUI
        Send commands to setup amplifier
        Store settings to self
        
        Returns: bool, whether or not setup was successful
        '''
        self._error_msg('setup_EIS')
        return
    
    
    def run_CV(self, path):
        '''
        Send command to run a CV using the current settings
        
        path: string, path to save to
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_CV')
        return
    
    
    def run_CA(self, path):
        '''
        Send command to run a CA using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_CA')
        return
    
    
    def run_EIS(self, path):
        '''
        Send command to run an EIS spectrum using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_EIS')
        return
    
    
    def run_custom(self, path):
        '''
        Send command to run the custom waveform using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_custom')
        return
    
    
    def run_OCP(self, path):
        '''
        Send command to run an OCP measurement
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_OCP')
        return
    
    
    def hold_potential(self, voltage):
        '''
        Send command to set the amplifier to hold a given potential
        
        Returns: string, path to saved data file
        '''
        self._error_msg('hold_potential')
        return
        


class HekaReader(Logger):
    
    def __init__(self, master, output_file):
        self.master = master
        self.master.register(self)
        self.file = output_file
        self.last_msg = None
        self.willStop = False
        if os.path.exists(self.file):
            with open(self.file, 'w') as f:
                f.close()
     
    def stop(self):
        self.willStop = True
        
    
    @threads.new_thread  
    def read(self):
        '''
        Called in its own thread. Continually reads HEKA output file and
        stores last response in self.last_msg
        
        Response has 2 lines:
            +0001                      // Response index
            Reply_whatever             // Response message
            
        Writer should check Reader.last_msg[0] to get index, [1] to get message
        '''
        self.log('Starting reading')
        while True:
            if (self.master.STOP or self.willStop):
                self.willStop = True
                break
            
            if not os.path.exists(self.file):
                continue

            with open(self.file, 'r') as f:
                lines = [line.rstrip() for line in f]
                if (lines != self.last and lines != None):
                    self.last_msg = lines
        self.log('Stopped reading')
    
    
    def wait_response(self, string, timeout=5):
        '''
        Waits until PATCHMASTER gives a response starting with given string.
        '''
        st = time.time()
        while time.time() - st < timeout:
            try:
                response = self.last_msg[1] 
                if response.startswith(string):
                    return response
            except:
                pass
        self.log(f'Error: Timed out waiting for response string:{string}')
        return None
        




class HEKA(Potentiostat):
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
    
    def __init__(self, master, input_file = input_file,
                 output_file = output_file):
        # Register to master
        self.master = master
        self.master.register(self, alias='Potentiostat')
        self.willStop = False
        
        # Clear input file
        self.file = input_file
        with open(self.file, 'w') as f:
            f.close()
        self.num = 0
        
        # Initialize Reader object
        self.Reader = HekaReader(master, output_file)
        
        # Initialize local parameter storage
        self.CV_params          = None
        self.EIS_params         = None
        self.EIS_WF_params      = None
        self.EIS_corrections    = None
    
    
    
    #####################################
    ####    PRIVATE HEKA COMMANDS    ####
    #####################################
    
    def _running(self):
        self.status = 'running'
        
    def _idle(self):
        self.status = 'idle'
    
    def _send_command(self, cmd):
        if self.master.TEST_MODE:
            return
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n{cmd}\n')
        self.num += 1
        time.sleep(0.1)
    
    def _send_multiple_cmds(self, cmds:list):
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n')
            for cmd in cmds:
                f.write(f'{cmd}\n')
        self.num += 1
        time.sleep(0.1)
        
    def _abort(self):
        '''
        Send commands to immediately stop and store the current measurement
        '''
        self._idle()
        self._send_multiple_cmds(['Set N Break 1',
                                  'Set N Stop 1'])
        self._idle()
        self._send_multiple_cmds(['Set N Break 1',
                                  'Set N Stop 1',
                                  'Set N Store 1'])
        self._idle()
        
        
    def _await(self, timeout):
        '''
        Wait for HEKA to finish a recording. Send status update queries and break
        when recording finishes
        '''
        st = time.time()
        while time.time() - st < timeout:
            if self.master.ABORT:
                self.abort()
                return 'abort'
            self._send_command('Query')
            try:
                if self.Reader.last_msg[1] == 'Query_Idle':
                    return 'success'
            except: pass
        return 'failed'
        
        
    def _save_last_experiment(self, path:str=None):
        '''
        Send commands to save the last run experiment to the given path
        
        There is a bug in PATCHMASTER which does not allow the
        "Export" macro to accept a user-defined path. So, we
        save to the default path (which is the same as the 
        current DataFile path) and copy the file to the desired path
        '''
        
        # Get path of the current DataFile, where PATCHMASTER will export to 
        self._send_command('GetParameters DataFile')
        response = self.Reader.wait_response('Reply_GetParameters', 1)
        if not response:
            return 
        savepath = response.lstrip('Reply_GetParameters ').strip('"')
        savepath = savepath.replace('.dat', '')
        savepath += '.asc'
        # Export as ASCII if not part of a hopping mode
        if (not path or path == 'None/.asc'):
            self._send_command('Set @  ExportTarget  "ASCII"')
            savepath += '.asc'
        # Otherwise export in MATLAB (binary) format b/c it's way faster
        else:
            self._send_command('Set @  ExportTarget  "MatLab"')
            savepath += '.mat'
        if os.path.exists(savepath):
            os.remove(savepath)
        
        
        # Select Series level for full export
        self._send_command('GetTarget')
        response = self.Reader.wait_response('Reply_GetTarget')
        if not response: 
            return
        dat = response.split('  ')[1]
        group, ser, sweep, trace, target = dat.split(',')
        self._send_command(f'SetTarget {group},{ser},{sweep},{trace},2,TRUE,TRUE')
            
        # Set oscilloscope to show full time, 0-> 100%. Otherwise,
        # PATCHMASTER only exports the times displayed on the scope
        time.sleep(0.1)
        self._send_multiple_cmds([f'Set O Xmin 0',
                                  f'Set O Xmax 100',
                                  f'Set O AutoSweep'])
        
        # Do the export
        self._send_command(f'Export overwrite, {savepath}')
        if not self.Reader.wait_response('Reply_Export', 30):
            return
         
        if (not path or path == 'None/.asc'): 
            # Data was not recorded as part of a scanning experiment
            # Save it with the timestamp
            self._send_command('GetParameters SeriesDate, SeriesTime')
            response = self.Reader.wait_response('Reply_GetParameters')
            if not response: return
            SeriesDate, SeriesTime = response.split(',')

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
    
    
    def _update_Values(self, values):
        cmds = []
        for i, val in values.items():
            cmds.append(f'SetValue {int(i)} {val}')
        cmds.append('ExecuteProtocol _update_pgf_params_') # Set PgfParams = Values
        self._send_multiple_cmds(cmds)
    
    
    def _make_EIS_waveform(self):
        pass
    
    
    def _check_EIS_corrections(self):
        pass
    
    
    def _get_EIS_filters(self):
        pass
    
    
    def _generate_CV_params(self, E0, E1, E2, E3, scan_rate, quiet_time):
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
        
    
    def _generate_EIS_params(self, E_DC, duration):
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
    
        
    
    
    
    ###################################
    ####    COMMON API COMMANDS    ####
    ###################################
    
    def stop(self):
        '''
        Called by master when program stops.
        
        For HEKA, just stop the reader thread.
        '''
        self.Reader.stop() 
        
    
    def isRunning(self):
        return self.status == 'running'
    
    
    def start_ADC(self, timeout):
        '''
        Send commands to start ADC polling
        '''
        run(partial(self.master.ADC.polling,
                    timeout=timeout))
    
    
    def stop_ADC(self):
        self.master.ADC.STOP_POLLING()
    
    
    def set_amplifier(self):
        '''
        Read amplifier settings from GUI
        Send commands to set amplifier (filters, gain, etc)
        
        Returns: bool, whether or not setup was successful
        '''
        parameters = self.master.GUI.get_amplifier_params()
        cmds = []
        for key, val in parameters.items():
            cmds.append(f'Set {key} {val}')
        cmds.append('Set E TestDacToStim1 0')
        self._send_multiple_cmds(cmds)
        return True
    
    
    def setup_CV(self):
        '''
        Read CV settings from GUI
        Send commands to setup PGF (voltages, times)
        Store settings to self
        
        Returns: bool, whether or not setup was successful
        '''
        # Pull parameters from GUI        
        parameters = self.master.GUI.get_CV_params()
        if parameters == (0,0,0,0,0,0):
            return False
        
        # Update Values in pgf
        values, duration = self._generate_CV_params(*parameters)
        self._update_Values(values)
        
        # Store locally
        self.CV_params = values
        self.CV_params['scan_rate'] = abs(values[2] - values[0])/values[3]
        self.CV_params['duration'] = duration
        
        self.log(f'Set CV parameters: {self.CV_params}', quiet=True)
        return
    
    
    def setup_EIS(self):
        '''
        Read EIS settings from GUI
        Make EIS waveform
        Send commands to setup PGF (E0, duration)
        Store settings to self
        
        Returns: None
        '''
        self._error_msg('setup_EIS')
        return
    
    
    def run_CV(self, path):
        '''
        path: string, path to save to
        
        Send command to run a CV using the current settings
        
        Returns: string, path to saved data file
        '''
        if self.isRunning():
            self.log('Error: received command to run CV but already running')
            return ''
        
        self._running()
        
        # Determine what sampling rate to use based on scan rate
        scan_rate = self.CV_params['scan_rate']
        if scan_rate <= 0.1:
            mode = '10Hz'
        elif scan_rate > 0.1 and scan_rate <= 0.5:
            mode = '100Hz'
        elif scan_rate > 0.5 and scan_rate <= 1:
            mode = '1kHz'
        elif scan_rate > 1:
            mode = '10kHz'
        
        sequence = f'_CV-{mode}'
        timeout = self.CV_params['duration'] + 3
        
        self.log(f'Running sequence {sequence}', quiet=True)
        self._send_command(f'ExecuteSequence {sequence}')
        self.start_ADC(timeout=timeout)
        
        success = self._await(timeout=timeout)
        
        self.stop_ADC()
        
        self._idle()
        
        if success == 'success':
            return self._save_last_experiment(path)
        
        return ''
    
    
    def run_CA(self):
        '''
        Send command to run a CA using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_CA')
        return
    
    
    def run_EIS(self):
        '''
        Send command to run an EIS spectrum using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_EIS')
        return
    
    
    def run_custom(self):
        '''
        Send command to run the custom waveform using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_custom')
        return
    
    
    def run_OCP(self):
        '''
        Send command to run an OCP measurement
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_OCP')
        return
    
    
    def hold_potential(self, voltage):
        '''
        Send command to set the amplifier to hold a given potential
        
        Returns: string, path to saved data file
        '''
        self._error_msg('hold_potential')
        return
    
    
    




class BioLogic(Potentiostat):
    
    
    def set_amplifier(self):
        '''
        Read amplifier settings from GUI
        Send commands to set amplifier
        
        Returns: None
        '''
        self._error_msg('set_amplifier')
        return
    
    
    def setup_CV(self):
        '''
        Read CV settings from GUI
        Send commands to setup amplifier
        Store settings to self
        
        Returns: None
        '''
        self._error_msg('setup_CV')
        return
    
    
    def setup_EIS(self):
        '''
        Read EIS settings from GUI
        Send commands to setup amplifier
        Store settings to self
        
        Returns: None
        '''
        self._error_msg('setup_EIS')
        return
    
    
    def run_CV(self):
        '''
        Send command to run a CV using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_CV')
        return
    
    
    def run_CA(self):
        '''
        Send command to run a CA using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_CA')
        return
    
    
    def run_EIS(self):
        '''
        Send command to run an EIS spectrum using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_EIS')
        return
    
    
    def run_custom(self):
        '''
        Send command to run the custom waveform using the current settings
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_custom')
        return
    
    
    def run_OCP(self):
        '''
        Send command to run an OCP measurement
        
        Returns: string, path to saved data file
        '''
        self._error_msg('run_OCP')
        return
    
    
    def hold_potential(self, voltage):
        '''
        Send command to set the amplifier to hold a given potential
        
        Returns: string, path to saved data file
        '''
        self._error_msg('hold_potential')
        return

