import time
import os
import psutil
import shutil
import json
import numpy as np
from tkinter import messagebox
from .FeedbackController import read_heka_data
from .DataStorage import EISDataPoint
from ..utils.utils import run, Logger
from ..utils.EIS_util import generate_tpl, get_EIS_sample_rate
from functools import partial


# HEKA file paths
input_file  = r'C:/ProgramData/HEKA/com/E9Batch.In'
output_file = r'C:/ProgramData/HEKA/com/E9Batch.Out'

DEFAULT_SAVE_PATH = r'D:/SECM/Data'


class Potentiostat():
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
        self.last = None
        self.willStop = False
        if os.path.exists(self.file):
            with open(self.file, 'w') as f:
                f.close()
     
    def stop(self):
        self.willStop = True
        
                
    def read(self):
        '''
        Called in its own thread. Continually reads HEKA output file and
        stores last response in self.last
        '''
        while True:
            if (self.master.STOP or self.willStop):
                self.willStop = True
                break
            
            if not os.path.exists(self.file):
                continue

            with open(self.file, 'r') as f:
                lines = [line.rstrip() for line in f]
                if (lines != self.last and lines != None):
                    self.last = lines
        self.log('Stopped reading')
    
    
    def wait_response(self, string, timeout=5):
        '''
        Waits until PATCHMASTER gives a response starting with given string.
        '''
        st = time.time()
        while time.time() - st < timeout:
            try:
                response = self.last[1]
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
        self.master.register(self)
        
        # Clear input file
        self.file = input_file
        with open(self.file, 'w') as f:
            f.close()
        self.num = 0
        
        # Initialize Reader object
        self.Reader = HekaReader(master, output_file)
        run(self.Reader.read)
        
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
    
    
    def _update_Values(self):
        pass
    
    
    def _make_EIS_waveform(self):
        pass
    
    
    def _check_EIS_corrections(self):
        pass
    
    
    def _get_EIS_filters(self):
        pass
    
    
    def _generate_CV_params(self):
        pass
    
    
    def _generate_EIS_params(self):
        pass
    
        
    
    
    
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

