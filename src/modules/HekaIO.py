import time
import os
import psutil
import shutil
import json
from collections import deque
import numpy as np
from tkinter import messagebox
from .FeedbackController import read_heka_data
from .DataStorage import EISDataPoint
from ..utils.utils import run, Logger
from ..utils.EIS_util import generate_tpl, get_EIS_sample_rate
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

        
class SharedHekaReader(Logger):
    '''
    Class for reading PATCHMASTER's responses in /E9Batch.Out
    
    The last response is stored in HekaReader.last and should be checked
    immediately after a command is sent, because it could get overwritten
    by a subsequent message
    '''
    def __init__(self, output_file=output_file):
        self.file = output_file
        self.last = None
        self.STOP = False
        self.isReading = False
        if os.path.exists(self.file):
            with open(self.file, 'w') as f: 
                f.close()
    
    def PatchmasterRunning(self, channel):
        # Checks if PATCHMASTER is currently running
        for p in psutil.process_iter():
            if 'PatchMaster.exe' in p.name():
                return True
        return False
    
    
    def read_stream(self):
        '''
        Call in its own thread. Reads HEKA output file continuously
        until receives stop command from master. Stores the last
        output in self.last.
        '''
        if self.isReading:
            # Other channel already initialized reading
            return
        
        while True:
            self.isReading = True
            if self.STOP:
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
    'Pass all commands to module shared between channels'
    def __init__(self, master, sharedWriter):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.Writer = sharedWriter
        run(self.check_for_stop)
    
    def __getattr__(self, name, *args, **kwargs):
        # func = partial(getattr(self.Writer, name), self.channel, *args, **kwargs)
        # self.Writer.add_to_queue(func)
        return partial(getattr(self.Writer, name), self.channel, *args, **kwargs)
     
    
    def check_for_stop(self):
        while True:
            if self.master.STOP:
                self.Writer.STOP = True
                self.Writer.Reader.STOP = True
                break
        self.log('Stopping')
        
    
    
        
           
        
        
        
class SharedHekaWriter(Logger):
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
    def __init__(self, Reader, input_file=input_file):
        self.STOP = False
        self.status = {1:'idle', 2:'idle'}
        self.queue = deque()
        
        self.Reader = Reader
        run(self.Reader.read_stream)
        
        self.file = input_file   # For EPC10 batch communication
        self.num = 0
        
        self.clear_file(1)
        self.send_command(1, 'Echo startup')
        self.send_command(1, 'SetSleep 0.01')
     
        
    def send_command(self, channel, cmd):
        # print(f'Sending: {self.num} {cmd}')
        # if self.master.TEST_MODE:
        #     return
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n{cmd}\n')
        self.num += 1
        time.sleep(0.1)
        
    
    def run_tasks(self):
        while True:
            if self.STOP:
                break
            if not len(self.queue):
                continue
            func = self.queue.popleft()
            func()
        return
    
    def append_task(self, function):
        self.queue.append(function)
        return
        
        
    def _schedule_task(self, function, delay):
        time.sleep(delay)
        self.append_task(function)
        return 
    
            
    def schedule_task(self, function:object, delay:float):
        '''
        Create a new thread which will wait for *delay* seconds 
        then put the function back in the queue
        '''
        run(partial(self._schedule_task, function, delay))
        return    
    
    
    # Return list of commands to send to set the Values in Patchmaster    
    # Values are used to dynamically set echem settings in the pgf file, 
    # for example, CV bounds or EIS duration
    def get_value_commands(self, values):
        cmds = []
        for i, val in values.items():
            cmds.append(f'SetValue {int(i)} {val}')
        return cmds
    
    
    # Get list of commands to reset amplifier to the default state
    def get_reset_amplifier_commands(self):
        cmds = ['Set E StimFilter 1',
                'Set E TestDacToStim1 0',
                'Set E Mode 3',
                'Set E Filter1 2',
                'Set E F2Response 0',
                'Set E Filter2 0.5']
        return cmds
        
    
    # Get list of commands to set amplifier and pgf to CV state
    def get_CV_setup_commands(self, channel, E0, E1, E2, E3, 
                              scan_rate, quiet_time):
        if scan_rate <= 0: 
            raise ValueError('Scan rate must be > 0')
        values, duration = generate_CV_params(E0, E1, E2, E3, 
                                              scan_rate, quiet_time)
        
        
        cmds = [f'Set E Ampl{channel} 1']
        cmds += get_value_commands(values)
        
        self.CV_params   = values
        self.CV_duration = duration
        self.log('Set CV parameters', 1)
        
        
    def set_amplifier(self, channel):
        pass
    
    
    def run_CV(self, channel):
        pass
   

    

   
        

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
        if filt*1000 >= 5*max_freq:
            best_filt1 = filt
            break
    best_filt2 = 5*max_freq
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



    