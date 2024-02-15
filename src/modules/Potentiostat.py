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
    
    EIS_applied_freqs = None
    EIS_corrections   = None
    
    def _error_msg(self, method_name):
        raise NotImplementedError(f'Method {method_name} not implemented in class {self.__class__}')
    
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
        


class HEKA(Potentiostat):
    
    def __init__(self, master, input_file = input_file,
                 output_file = output_file):
        self.master = master
        self.master.register(self)
        
    
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

